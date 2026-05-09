"""Subcommand dispatcher: `prepare` (gather data) -> agent decides -> `emit-signal` -> `finish-run`."""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from lib import brief, discord, market_data, supabase_client, technicals
from lib.logging import setup_logging
from lib.models import Signal

log = logging.getLogger(__name__)


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
    emit.add_argument("--dry-run", action="store_true", help="No DB write, no Discord post.")
    emit.add_argument("--verbose", action="store_true", help="DEBUG logging.")

    fin = sub.add_parser("finish-run", help="Close out the analysis_runs row.")
    fin.add_argument("--run-id", required=True, type=_parse_uuid)
    fin.add_argument("--status", required=True, choices=("success", "partial", "failed"))
    fin.add_argument("--error", default=None)
    fin.add_argument("--profile-count", type=int, default=0)
    fin.add_argument("--signal-count", type=int, default=0)
    fin.add_argument("--dry-run", action="store_true", help="No Supabase write.")
    fin.add_argument("--verbose", action="store_true", help="DEBUG logging.")

    return p


def cmd_prepare(args: argparse.Namespace) -> int:
    market_data.clear_cache()

    profiles = supabase_client.get_active_profiles()
    if args.profile:
        profiles = [p for p in profiles if p.slug == args.profile]
        if not profiles:
            log.error("no active profile matched slug %r", args.profile)
            return 2

    started_at = datetime.now(timezone.utc)
    run_id: UUID = uuid4() if args.dry_run else supabase_client.start_run()

    profile_sections: list[dict] = []
    for profile in profiles:
        holdings = supabase_client.get_holdings(profile.id)
        if args.ticker:
            holdings = [h for h in holdings if h.ticker == args.ticker]

        holding_sections: list[dict] = []
        for holding in holdings:
            try:
                prices = market_data.get_price_history(holding.ticker, period="6mo")
                if prices is None or prices.empty:
                    log.warning("skipping %s: no price data", holding.ticker)
                    continue
                indicators = technicals.compute_indicators(prices)
                holding_sections.append(brief.build_holding_section(holding, prices, indicators))
            except Exception:
                log.exception("failed to gather %s/%s", profile.slug, holding.ticker)

        if holding_sections:
            profile_sections.append(brief.build_profile_section(profile, holding_sections))

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

    ctx = discord.HoldingContext(
        quantity=holding_section.get("quantity"),
        cost_basis_dkk=holding_section.get("cost_basis_dkk"),
        current_value_dkk=holding_section.get("current_value_dkk"),
        pnl_pct=holding_section.get("pnl_pct"),
        is_watchlist=(holding_section.get("kind") == "watchlist"),
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


_DISPATCH = {
    "prepare": cmd_prepare,
    "emit-signal": cmd_emit_signal,
    "finish-run": cmd_finish_run,
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
