"""Thin orchestrator: iterate profiles -> holdings, fan out to lib/* helpers."""

import argparse
import logging
import sys
from uuid import uuid4

from lib import analyzer, discord, market_data
from lib import news as news_module
from lib import supabase_client, technicals
from lib.logging import setup_logging

log = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="run_analysis", description="Stock analysis routine.")
    p.add_argument("--profile", help="Limit to a single profile slug.")
    p.add_argument("--ticker", help="Limit to a single ticker symbol.")
    p.add_argument("--dry-run", action="store_true", help="No DB writes, no Discord posts.")
    p.add_argument("--verbose", action="store_true", help="DEBUG logging.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(verbose=args.verbose)
    market_data.clear_cache()

    profiles = supabase_client.get_active_profiles()
    if args.profile:
        profiles = [p for p in profiles if p.slug == args.profile]
        if not profiles:
            log.error("no active profile matched slug %r", args.profile)
            return 2

    run_id = uuid4() if args.dry_run else supabase_client.start_run()
    signal_count = 0
    status: str = "success"
    error: str | None = None

    try:
        for profile in profiles:
            holdings = supabase_client.get_holdings(profile.id)
            if args.ticker:
                holdings = [h for h in holdings if h.ticker == args.ticker]

            for holding in holdings:
                try:
                    prices = market_data.get_price_history(holding.ticker, period="6mo")
                    if prices is None or prices.empty:
                        log.warning("skipping %s: no price data", holding.ticker)
                        continue

                    indicators = technicals.compute_indicators(prices)
                    news = news_module.fetch_news_digest(holding.ticker, holding.name)
                    signal = analyzer.analyze_holding(holding, prices, indicators, news)
                    signal.run_id = run_id
                    signal.profile_id = profile.id

                    if not args.dry_run:
                        supabase_client.insert_signal(signal)

                    discord.post_signal(
                        signal=signal,
                        profile=profile,
                        indicators=indicators,
                        position_dkk=holding.position_dkk,
                        is_watchlist=(holding.kind == "watchlist"),
                        dry_run=args.dry_run,
                    )
                    signal_count += 1
                except Exception:
                    log.exception("failed for %s/%s", profile.slug, holding.ticker)
                    status = "partial"
    except Exception as e:
        status = "failed"
        error = str(e)
        raise
    finally:
        if not args.dry_run:
            try:
                supabase_client.finish_run(
                    run_id=run_id,
                    status=status,  # type: ignore[arg-type]
                    profile_count=len(profiles),
                    signal_count=signal_count,
                    error=error,
                )
            except Exception:
                log.exception("failed to finalize analysis_run row")

    log.info("done: status=%s profiles=%d signals=%d", status, len(profiles), signal_count)
    return 0 if status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
