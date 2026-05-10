"""Discord webhook poster with embed formatting and one 429-aware retry."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import requests

from .config import get_settings
from .models import Indicators, Profile, Signal

log = logging.getLogger(__name__)

_COLORS: dict[str, int] = {
    "BUY": 0x16A34A,
    "SELL": 0xDC2626,
    "HOLD": 0x6B7280,
}

_HOLD_REASON_MAX = 200
_DESCRIPTION_MAX = 4000


@dataclass(frozen=True)
class HoldingContext:
    """Per-holding numbers needed by the embed; all None for watchlist."""

    quantity: float | None
    cost_basis: float | None
    current_value: float | None
    pnl_pct: float | None
    currency: str
    is_watchlist: bool


@dataclass(frozen=True)
class HoldSummaryItem:
    """One ticker's slice of a batched HOLD summary post."""

    ticker: str
    current_price: float
    currency: str
    rsi_14: float | None
    confidence: float
    reasoning: str
    is_watchlist: bool
    pnl_pct: float | None


def _truncate(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def _fmt_money(n: float | None) -> str:
    return "n/a" if n is None else f"{n:,.0f}".replace(",", ".")


def _fmt_qty(n: float | None) -> str:
    if n is None:
        return "n/a"
    # Strip trailing zeros for whole-share counts.
    return f"{n:.4f}".rstrip("0").rstrip(".") or "0"


def _fmt_pnl_pct(p: float | None) -> str:
    if p is None:
        return "n/a"
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.1f}%"


def _position_fields(ctx: HoldingContext) -> list[dict]:
    if ctx.is_watchlist:
        return [{"name": "Position", "value": "Watchlist", "inline": True}]
    now_value = (
        f"{_fmt_money(ctx.current_value)} ({_fmt_pnl_pct(ctx.pnl_pct)})"
        if ctx.current_value is not None
        else "n/a"
    )
    return [
        {"name": "Qty", "value": _fmt_qty(ctx.quantity), "inline": True},
        {"name": f"Cost ({ctx.currency})", "value": _fmt_money(ctx.cost_basis), "inline": True},
        {"name": f"Now ({ctx.currency})", "value": now_value, "inline": True},
    ]


def build_payload(
    signal: Signal,
    profile: Profile,
    indicators: Indicators,
    ctx: HoldingContext,
    using_fallback: bool,
) -> dict:
    title = f"{signal.signal_type} {signal.ticker}"
    if using_fallback:
        title = f"[{profile.name}] {title}"

    rsi = f"{indicators.rsi_14:.1f}" if indicators.rsi_14 is not None else "n/a"
    price = f"{indicators.last_close:.2f}"

    fields: list[dict] = [
        {"name": f"Price ({ctx.currency})", "value": price, "inline": True},
        {"name": "RSI14", "value": rsi, "inline": True},
        *_position_fields(ctx),
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


def _post_with_retry(webhook: str, payload: dict, label: str) -> None:
    for attempt in (1, 2):
        resp = requests.post(webhook, json=payload, timeout=15)
        if resp.status_code == 429 and attempt == 1:
            retry_after = float(resp.headers.get("Retry-After", "1"))
            log.warning("discord 429 (%s); sleeping %.2fs before retry", label, retry_after)
            time.sleep(retry_after)
            continue
        if resp.status_code >= 400:
            log.error(
                "discord post failed (%s) %s: %s", label, resp.status_code, resp.text[:200]
            )
            resp.raise_for_status()
        return


def post_signal(
    signal: Signal,
    profile: Profile,
    indicators: Indicators,
    ctx: HoldingContext,
    dry_run: bool = False,
) -> None:
    settings = get_settings()
    using_fallback = not profile.discord_webhook_url
    webhook = profile.discord_webhook_url or settings.default_discord_webhook_url

    payload = build_payload(
        signal=signal,
        profile=profile,
        indicators=indicators,
        ctx=ctx,
        using_fallback=using_fallback,
    )

    if dry_run:
        log.info("[dry-run] would POST to discord: %s", payload["embeds"][0]["title"])
        return

    _post_with_retry(webhook, payload, label=f"signal {signal.signal_type} {signal.ticker}")


def _hold_summary_line(item: HoldSummaryItem) -> str:
    watch_tag = " [W]" if item.is_watchlist else ""
    rsi_str = f"RSI {item.rsi_14:.0f}" if item.rsi_14 is not None else "RSI n/a"
    conf_str = f"{item.confidence * 100:.0f}%"
    pnl_str = ""
    if not item.is_watchlist and item.pnl_pct is not None:
        sign = "+" if item.pnl_pct >= 0 else ""
        pnl_str = f" · {sign}{item.pnl_pct:.1f}%"
    header = (
        f"**{item.ticker}**{watch_tag} · "
        f"{item.current_price:.2f} {item.currency} · "
        f"{rsi_str} · {conf_str}{pnl_str}"
    )
    reason = _truncate(item.reasoning.strip(), _HOLD_REASON_MAX)
    return f"{header}\n{reason}"


def build_hold_summary_payload(
    items: list[HoldSummaryItem],
    profile: Profile,
    run_id: UUID | None,
    using_fallback: bool,
) -> dict:
    title = f"📊 HOLD Summary ({len(items)})"
    if using_fallback:
        title = f"[{profile.name}] {title}"

    description = _truncate("\n\n".join(_hold_summary_line(i) for i in items), _DESCRIPTION_MAX)

    run_short = str(run_id)[:8] if run_id else "dry-run"
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": _COLORS["HOLD"],
                "footer": {"text": f"run {run_short} | {ts}"},
            }
        ]
    }


def post_hold_summary(
    items: list[HoldSummaryItem],
    profile: Profile,
    run_id: UUID | None,
    dry_run: bool = False,
) -> None:
    if not items:
        return
    settings = get_settings()
    using_fallback = not profile.discord_webhook_url
    webhook = profile.discord_webhook_url or settings.default_discord_webhook_url

    payload = build_hold_summary_payload(
        items=items, profile=profile, run_id=run_id, using_fallback=using_fallback
    )

    if dry_run:
        log.info(
            "[dry-run] would POST hold summary (%d tickers) for profile %s",
            len(items),
            profile.slug,
        )
        return

    _post_with_retry(webhook, payload, label=f"hold-summary {profile.slug}")
