"""Subcommand dispatcher: `prepare` (gather data) -> agent decides -> `emit-signal` -> `finish-run`."""

import argparse
import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from lib import brief, discord, market_data, supabase_client, technicals
from lib.logging import setup_logging
from lib.models import Profile, Signal

log = logging.getLogger(__name__)

DEFAULT_HOLDS_PATH = "/tmp/stock-analysis-holds.json"


def _parse_uuid(s: str) -> UUID:
    try:
        return UUID(s)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"not a UUID: {s!r}") from e


def _parse_confidence(s: str) -> float:
    try:
        v = float(s)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"not a float: {s!r}") from e
    if not 0.0 <= v <= 1.0:
        raise argparse.ArgumentTypeError(f"confidence must be in [0, 1]: {v}")
    return v


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="run_analysis", description="Stock analysis routine.")
    sub = p.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare", help="Gather price + indicator data; write brief JSON.")
    prep.add_argument("--profile", help="Limit to a single profile slug.")
    prep.add_argument("--ticker", help="Limit to a single ticker symbol.")
    prep.add_argument(
        "--brief-path",
        default=brief.DEFAULT_BRIEF_PATH,
        help=f"Where to write the brief (default: {brief.DEFAULT_BRIEF_PATH}).",
    )
    prep.add_argument(
        "--holds-path",
        default=DEFAULT_HOLDS_PATH,
        help=f"Where the HOLD queue is staged (default: {DEFAULT_HOLDS_PATH}).",
    )
    prep.add_argument("--dry-run", action="store_true", help="Skip Supabase run row insert.")
    prep.add_argument("--verbose", action="store_true", help="DEBUG logging.")

    emit = sub.add_parser("emit-signal", help="Commit one signal: insert row + post Discord.")
    emit.add_argument("--run-id", required=True, type=_parse_uuid)
    emit.add_argument("--profile-id", required=True, type=_parse_uuid)
    emit.add_argument("--ticker", required=True)
    emit.add_argument("--signal", required=True, choices=("BUY", "SELL", "HOLD"))
    emit.add_argument("--confidence", required=True, type=_parse_confidence)
    emit.add_argument("--reasoning", required=True)
    emit.add_argument(
        "--brief-path",
        default=brief.DEFAULT_BRIEF_PATH,
        help=f"Brief JSON to read price/indicator context from (default: {brief.DEFAULT_BRIEF_PATH}).",
    )
    emit.add_argument(
        "--holds-path",
        default=DEFAULT_HOLDS_PATH,
        help=f"Where to queue HOLD signals for the batched summary (default: {DEFAULT_HOLDS_PATH}).",
    )
    emit.add_argument("--dry-run", action="store_true", help="No DB write, no Discord post.")
    emit.add_argument("--verbose", action="store_true", help="DEBUG logging.")

    fin = sub.add_parser("finish-run", help="Close out the analysis_runs row.")
    fin.add_argument("--run-id", required=True, type=_parse_uuid)
    fin.add_argument("--status", required=True, choices=("success", "partial", "failed"))
    fin.add_argument("--error", default=None)
    fin.add_argument("--profile-count", type=int, default=0)
    fin.add_argument("--signal-count", type=int, default=0)
    fin.add_argument(
        "--holds-path",
        default=DEFAULT_HOLDS_PATH,
        help=f"Where the HOLD queue was staged (default: {DEFAULT_HOLDS_PATH}).",
    )
    fin.add_argument("--dry-run", action="store_true", help="No Supabase write.")
    fin.add_argument("--verbose", action="store_true", help="DEBUG logging.")

    score = sub.add_parser(
        "score-signals",
        help="Backfill realised T+5 / T+30 returns onto past signals (separate cron task).",
    )
    score.add_argument(
        "--window",
        choices=("5", "30", "both"),
        default="both",
        help="Which outcome window(s) to score (default: both).",
    )
    score.add_argument("--batch", type=int, default=200, help="Max signals per window per run.")
    score.add_argument("--dry-run", action="store_true", help="No Supabase update.")
    score.add_argument("--verbose", action="store_true", help="DEBUG logging.")

    return p


def _read_holds_queue(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        log.warning("hold queue at %s unreadable; resetting", path)
        return {}


def _write_holds_queue(path: Path, queue: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, indent=2, default=str), encoding="utf-8")


def _clear_holds_queue(path: Path) -> None:
    if path.exists():
        path.unlink()


def _enqueue_hold(
    path: Path,
    run_id: UUID,
    profile: Profile,
    item: discord.HoldSummaryItem,
) -> None:
    queue = _read_holds_queue(path)
    if queue.get("run_id") and queue.get("run_id") != str(run_id):
        queue = {}
    queue.setdefault("run_id", str(run_id))
    profiles = queue.setdefault("profiles", {})
    bucket = profiles.setdefault(
        str(profile.id),
        {
            "profile": {
                "id": str(profile.id),
                "slug": profile.slug,
                "name": profile.name,
                "discord_webhook_url": profile.discord_webhook_url,
            },
            "items": [],
        },
    )
    bucket["items"].append(asdict(item))
    _write_holds_queue(path, queue)


def _flush_holds_queue(path: Path, run_id: UUID, dry_run: bool) -> None:
    queue = _read_holds_queue(path)
    if not queue:
        return
    if queue.get("run_id") != str(run_id):
        log.info(
            "hold queue is for run %s, not %s; leaving it alone",
            queue.get("run_id"),
            run_id,
        )
        return

    for bucket in queue.get("profiles", {}).values():
        prof_data = bucket["profile"]
        profile = Profile(
            id=UUID(prof_data["id"]),
            slug=prof_data["slug"],
            name=prof_data["name"],
            discord_webhook_url=prof_data.get("discord_webhook_url"),
            is_active=True,
        )
        items = [
            discord.HoldSummaryItem(
                ticker=d["ticker"],
                current_price=float(d["current_price"]),
                currency=d["currency"],
                rsi_14=d.get("rsi_14"),
                confidence=float(d["confidence"]),
                reasoning=d["reasoning"],
                is_watchlist=bool(d["is_watchlist"]),
                pnl_pct=d.get("pnl_pct"),
            )
            for d in bucket.get("items", [])
        ]
        try:
            discord.post_hold_summary(items, profile, run_id, dry_run=dry_run)
        except Exception:
            log.exception("failed to post hold summary for profile %s", profile.slug)

    if not dry_run:
        _clear_holds_queue(path)


def cmd_prepare(args: argparse.Namespace) -> int:
    market_data.clear_cache()
    _clear_holds_queue(Path(args.holds_path))

    profiles = supabase_client.get_active_profiles()
    if args.profile:
        profiles = [p for p in profiles if p.slug == args.profile]
        if not profiles:
            log.error("no active profile matched slug %r", args.profile)
            return 2

    started_at = datetime.now(timezone.utc)
    run_id: UUID = uuid4() if args.dry_run else supabase_client.start_run()

    profile_sections: list[dict] = []
    today = datetime.now(timezone.utc).date()
    for profile in profiles:
        holdings = supabase_client.get_holdings(profile.id)
        if args.ticker:
            holdings = [h for h in holdings if h.ticker == args.ticker]

        signal_history_by_ticker: dict = {}
        if holdings and not args.dry_run:
            try:
                signal_history_by_ticker = supabase_client.get_recent_signals_for_holdings(
                    profile.id, [h.ticker for h in holdings]
                )
            except Exception:
                log.exception("failed to load signal history for profile %s", profile.slug)

        # Per-profile portfolio totals — built from cost basis up front, current value
        # filled in as we compute current_price for each holding.
        portfolio_totals: dict[str, dict] = {}
        for h in holdings:
            cur = (h.currency or "DKK").upper()
            bucket = portfolio_totals.setdefault(
                cur,
                {"total_cost_basis": 0.0, "total_current_value": 0.0, "holding_count": 0},
            )
            if h.quantity is not None and h.avg_buy_price is not None:
                bucket["total_cost_basis"] += float(h.quantity) * float(h.avg_buy_price)
            bucket["holding_count"] += 1

        holding_sections: list[dict] = []
        for holding in holdings:
            try:
                prices = market_data.get_price_history(holding.ticker, period="2y")
                if prices is None or prices.empty:
                    log.warning("skipping %s: no price data", holding.ticker)
                    continue
                indicators = technicals.compute_indicators(prices)
                current_price = float(prices["Close"].astype(float).iloc[-1])
                currency = (holding.currency or "DKK").upper()

                # Update current value running total for this currency.
                if holding.quantity is not None:
                    portfolio_totals.setdefault(
                        currency,
                        {"total_cost_basis": 0.0, "total_current_value": 0.0, "holding_count": 0},
                    )["total_current_value"] += float(holding.quantity) * current_price

                cal = market_data.get_earnings_calendar(holding.ticker)
                realtime = market_data.get_realtime_quote(holding.ticker)
                analyst = market_data.get_analyst_consensus(holding.ticker)
                fundamentals = market_data.get_fundamentals(holding.ticker)
                insider = market_data.get_insider_activity(holding.ticker)

                implied_move = None
                if cal.next_future is not None:
                    days_until = (cal.next_future.date() - today).days
                    if 0 <= days_until <= 14:
                        implied_move = market_data.get_earnings_implied_move(
                            holding.ticker, current_price, cal.next_future
                        )

                cost_basis = (
                    float(holding.quantity) * float(holding.avg_buy_price)
                    if holding.quantity is not None and holding.avg_buy_price is not None
                    else None
                )
                cur_total = portfolio_totals.get(currency, {}).get("total_cost_basis", 0.0)
                position_weight_pct = (
                    cost_basis / cur_total * 100.0
                    if cost_basis is not None and cur_total > 0
                    else None
                )

                baseline_idx = market_data.get_index_for_ticker(holding.ticker)
                baseline_prices = market_data.get_price_history(baseline_idx, period="2y")
                baseline_pct_30d = technicals.pct_change_30d_from_frame(baseline_prices)
                rel_strength_pct = (
                    indicators.pct_change_30d - baseline_pct_30d
                    if indicators.pct_change_30d is not None and baseline_pct_30d is not None
                    else None
                )
                relative_strength = {
                    "baseline_index": baseline_idx,
                    "baseline_pct_change_30d": (
                        round(baseline_pct_30d, 3) if baseline_pct_30d is not None else None
                    ),
                    "relative_strength_30d_pct": (
                        round(rel_strength_pct, 3) if rel_strength_pct is not None else None
                    ),
                }

                holding_sections.append(
                    brief.build_holding_section(
                        holding,
                        prices,
                        indicators,
                        last_earnings_date=cal.last_past,
                        next_earnings_date=cal.next_future,
                        signal_history=signal_history_by_ticker.get(holding.ticker),
                        realtime=realtime,
                        analyst=analyst,
                        relative_strength=relative_strength,
                        fundamentals=fundamentals,
                        insider=insider,
                        implied_move=implied_move,
                        position_weight_pct=position_weight_pct,
                    )
                )
            except Exception:
                log.exception("failed to gather %s/%s", profile.slug, holding.ticker)

        # Round the running totals before emitting; FX rates per profile.
        for bucket in portfolio_totals.values():
            bucket["total_cost_basis"] = round(bucket["total_cost_basis"], 2)
            bucket["total_current_value"] = round(bucket["total_current_value"], 2)
        fx_rates = market_data.get_fx_rates({h.currency for h in holdings if h.currency}, home="USD")

        if holding_sections:
            profile_sections.append(
                brief.build_profile_section(
                    profile,
                    holding_sections,
                    portfolio_totals=portfolio_totals,
                    fx_rates=fx_rates,
                )
            )

    payload = brief.build_brief(run_id, started_at, profile_sections)

    out_path = Path(args.brief_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print(f"run_id={run_id}")
    print(f"brief_path={out_path}")
    log.info(
        "prepare: profiles=%d holdings=%d brief=%s",
        len(profile_sections),
        sum(len(p["holdings"]) for p in profile_sections),
        out_path,
    )
    return 0


def _load_brief(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"brief not found at {path}; run `prepare` first")
    return json.loads(path.read_text(encoding="utf-8"))


def _find_holding(brief_data: dict, profile_id: UUID, ticker: str) -> dict | None:
    for prof in brief_data.get("profiles", []):
        if prof.get("id") == str(profile_id):
            for h in prof.get("holdings", []):
                if h.get("ticker") == ticker:
                    return h
    return None


def _indicators_from_brief(holding_section: dict):
    from lib.models import Indicators

    ind = holding_section.get("indicators", {})
    return Indicators(
        last_close=float(holding_section["current_price"]),
        rsi_14=ind.get("rsi_14"),
        sma_20=ind.get("sma_20"),
        sma_50=ind.get("sma_50"),
        sma_200=ind.get("sma_200"),
        macd=ind.get("macd"),
        macd_signal=ind.get("macd_signal"),
        pct_change_30d=ind.get("pct_change_30d"),
    )


def cmd_emit_signal(args: argparse.Namespace) -> int:
    brief_data = _load_brief(Path(args.brief_path))
    holding_section = _find_holding(brief_data, args.profile_id, args.ticker)
    if holding_section is None:
        log.error(
            "no holding %s found for profile %s in brief %s",
            args.ticker,
            args.profile_id,
            args.brief_path,
        )
        return 2

    profile = supabase_client.get_profile(args.profile_id)
    indicators = _indicators_from_brief(holding_section)

    signal = Signal(
        ticker=args.ticker,
        signal_type=args.signal,
        reasoning=args.reasoning,
        confidence=args.confidence,
        profile_id=args.profile_id,
        run_id=args.run_id,
    )

    if not args.dry_run:
        supabase_client.insert_signal(signal)

    currency = holding_section.get("currency") or "DKK"
    is_watchlist = holding_section.get("kind") == "watchlist"

    if args.signal == "HOLD":
        item = discord.HoldSummaryItem(
            ticker=args.ticker,
            current_price=float(holding_section["current_price"]),
            currency=currency,
            rsi_14=indicators.rsi_14,
            confidence=args.confidence,
            reasoning=args.reasoning,
            is_watchlist=is_watchlist,
            pnl_pct=holding_section.get("pnl_pct"),
        )
        if args.dry_run:
            log.info("[dry-run] would queue HOLD %s for batched summary", args.ticker)
        else:
            _enqueue_hold(Path(args.holds_path), args.run_id, profile, item)
        log.info("emit-signal ok: HOLD %s conf=%.2f (queued)", args.ticker, args.confidence)
        return 0

    ctx = discord.HoldingContext(
        quantity=holding_section.get("quantity"),
        cost_basis=holding_section.get("cost_basis"),
        current_value=holding_section.get("current_value"),
        pnl_pct=holding_section.get("pnl_pct"),
        currency=currency,
        is_watchlist=is_watchlist,
    )
    discord.post_signal(
        signal=signal,
        profile=profile,
        indicators=indicators,
        ctx=ctx,
        dry_run=args.dry_run,
    )

    log.info("emit-signal ok: %s %s conf=%.2f", args.signal, args.ticker, args.confidence)
    return 0


def cmd_finish_run(args: argparse.Namespace) -> int:
    _flush_holds_queue(Path(args.holds_path), args.run_id, dry_run=args.dry_run)

    if args.dry_run:
        log.info(
            "[dry-run] would finalize run %s status=%s profiles=%d signals=%d",
            args.run_id,
            args.status,
            args.profile_count,
            args.signal_count,
        )
        return 0
    supabase_client.finish_run(
        run_id=args.run_id,
        status=args.status,  # type: ignore[arg-type]
        profile_count=args.profile_count,
        signal_count=args.signal_count,
        error=args.error,
    )
    log.info("finish-run ok: %s status=%s", args.run_id, args.status)
    return 0


def _score_one_window(window_days: int, batch: int, dry_run: bool) -> tuple[int, int]:
    """Returns (scored, skipped). Skipped = no price coverage on either anchor."""
    pending = supabase_client.get_signals_needing_outcome(window_days, batch=batch)
    if not pending:
        log.info("score-signals: no pending signals for T+%d", window_days)
        return 0, 0

    by_ticker: dict[str, list] = {}
    for sig in pending:
        by_ticker.setdefault(sig.ticker, []).append(sig)

    scored = skipped = 0
    for ticker, sigs in by_ticker.items():
        prices = market_data.get_price_history(ticker, period="2y")
        if prices is None or prices.empty or "Close" not in prices.columns:
            log.warning("score-signals: no price history for %s; skipping %d signals", ticker, len(sigs))
            skipped += len(sigs)
            continue
        closes = prices["Close"].astype(float)
        idx = prices.index
        # idx may be tz-naive (yfinance often emits naive UTC daily bars).
        if getattr(idx, "tz", None) is None:
            idx = idx.tz_localize("UTC")
        for sig in sigs:
            if sig.id is None:
                skipped += 1
                continue
            anchor_a = sig.generated_at
            anchor_b = sig.generated_at + timedelta(days=window_days)
            try:
                pos_a = idx.searchsorted(anchor_a, side="left")
                pos_b = idx.searchsorted(anchor_b, side="left")
            except Exception:
                skipped += 1
                continue
            if pos_a >= len(closes) or pos_b >= len(closes):
                # Not yet enough trading days past the second anchor.
                skipped += 1
                continue
            price_a = float(closes.iloc[pos_a])
            price_b = float(closes.iloc[pos_b])
            if not price_a:
                skipped += 1
                continue
            outcome_pct = (price_b - price_a) / price_a * 100.0
            if dry_run:
                log.info(
                    "[dry-run] would set signal %s outcome_t%d_pct = %.2f",
                    sig.id,
                    window_days,
                    outcome_pct,
                )
            else:
                supabase_client.update_signal_outcome(sig.id, window_days, outcome_pct)
            scored += 1
    return scored, skipped


def cmd_score_signals(args: argparse.Namespace) -> int:
    market_data.clear_cache()
    windows: list[int] = [5, 30] if args.window == "both" else [int(args.window)]
    total_scored = total_skipped = 0
    for w in windows:
        scored, skipped = _score_one_window(w, args.batch, args.dry_run)
        log.info("score-signals: T+%d scored=%d skipped=%d", w, scored, skipped)
        total_scored += scored
        total_skipped += skipped
    log.info("score-signals done: scored=%d skipped=%d", total_scored, total_skipped)
    return 0


_DISPATCH = {
    "prepare": cmd_prepare,
    "emit-signal": cmd_emit_signal,
    "finish-run": cmd_finish_run,
    "score-signals": cmd_score_signals,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(verbose=args.verbose)
    try:
        return _DISPATCH[args.command](args)
    except Exception:
        log.exception("%s failed", args.command)
        return 1


if __name__ == "__main__":
    sys.exit(main())
