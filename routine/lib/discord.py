"""Discord webhook poster with embed formatting and one 429-aware retry."""

import logging
import time
from datetime import datetime, timezone

import requests

from .config import get_settings
from .models import Indicators, Profile, Signal

log = logging.getLogger(__name__)

_COLORS: dict[str, int] = {
    "BUY": 0x16A34A,
    "SELL": 0xDC2626,
    "HOLD": 0x6B7280,
}


def _truncate(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def build_payload(
    signal: Signal,
    profile: Profile,
    indicators: Indicators,
    position_dkk: float | None,
    is_watchlist: bool,
    using_fallback: bool,
) -> dict:
    title = f"{signal.signal_type} {signal.ticker}"
    if using_fallback:
        title = f"[{profile.name}] {title}"

    rsi = f"{indicators.rsi_14:.1f}" if indicators.rsi_14 is not None else "n/a"
    price = f"{indicators.last_close:.2f}"
    position_field = (
        "Watchlist" if is_watchlist or position_dkk is None else f"{position_dkk:.0f} DKK"
    )

    fields = [
        {"name": "Price (DKK)", "value": price, "inline": True},
        {"name": "RSI14", "value": rsi, "inline": True},
        {"name": "Position", "value": position_field, "inline": True},
        {"name": "Confidence", "value": f"{signal.confidence * 100:.0f}%", "inline": True},
        {"name": "Reasoning", "value": _truncate(signal.reasoning, 1024), "inline": False},
    ]

    run_short = str(signal.run_id)[:8] if signal.run_id else "dry-run"
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "embeds": [
            {
                "title": title,
                "color": _COLORS.get(signal.signal_type, 0x6B7280),
                "fields": fields,
                "footer": {"text": f"run {run_short} | {ts}"},
            }
        ]
    }


def post_signal(
    signal: Signal,
    profile: Profile,
    indicators: Indicators,
    position_dkk: float | None = None,
    is_watchlist: bool = False,
    dry_run: bool = False,
) -> None:
    settings = get_settings()
    using_fallback = not profile.discord_webhook_url
    webhook = profile.discord_webhook_url or settings.default_discord_webhook_url

    payload = build_payload(
        signal=signal,
        profile=profile,
        indicators=indicators,
        position_dkk=position_dkk,
        is_watchlist=is_watchlist,
        using_fallback=using_fallback,
    )

    if dry_run:
        log.info("[dry-run] would POST to discord: %s", payload["embeds"][0]["title"])
        return

    for attempt in (1, 2):
        resp = requests.post(webhook, json=payload, timeout=15)
        if resp.status_code == 429 and attempt == 1:
            retry_after = float(resp.headers.get("Retry-After", "1"))
            log.warning("discord 429; sleeping %.2fs before retry", retry_after)
            time.sleep(retry_after)
            continue
        if resp.status_code >= 400:
            log.error("discord post failed %s: %s", resp.status_code, resp.text[:200])
            resp.raise_for_status()
        return
