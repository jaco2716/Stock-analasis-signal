"""Build the analysis brief — the JSON contract between `prepare` and the agent."""

from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import pandas as pd

from .models import Holding, Indicators, Profile, SignalRecord

DEFAULT_BRIEF_PATH = "/tmp/stock-analysis-brief.json"

_RECENT_CLOSES = 10
_LOOKBACK_52W = 252
_VOLUME_AVG_DAYS = 20


def _golden_cross(indicators: Indicators) -> bool:
    return (
        indicators.sma_50 is not None
        and indicators.sma_200 is not None
        and indicators.sma_50 > indicators.sma_200
    )


def _death_cross(indicators: Indicators) -> bool:
    return (
        indicators.sma_50 is not None
        and indicators.sma_200 is not None
        and indicators.sma_50 < indicators.sma_200
    )


def _macd_histogram(indicators: Indicators) -> float | None:
    if indicators.macd is None or indicators.macd_signal is None:
        return None
    return float(indicators.macd - indicators.macd_signal)


def _atr_pct_of_price(indicators: Indicators) -> float | None:
    if indicators.atr_14 is None or not indicators.last_close:
        return None
    return float(indicators.atr_14 / indicators.last_close * 100.0)


def _high_low_52w(prices: pd.DataFrame, current_price: float) -> dict[str, float | None]:
    if len(prices) < _VOLUME_AVG_DAYS or "High" not in prices.columns or "Low" not in prices.columns:
        return {
            "high_52w": None,
            "low_52w": None,
            "pct_below_52w_high": None,
            "pct_above_52w_low": None,
        }
    window = prices.tail(_LOOKBACK_52W)
    hi = float(window["High"].astype(float).max())
    lo = float(window["Low"].astype(float).min())
    return {
        "high_52w": round(hi, 4),
        "low_52w": round(lo, 4),
        "pct_below_52w_high": round((current_price / hi - 1.0) * 100.0, 2) if hi else None,
        "pct_above_52w_low": round((current_price / lo - 1.0) * 100.0, 2) if lo else None,
    }


def _volume_context(prices: pd.DataFrame) -> dict[str, float | None]:
    if "Volume" not in prices.columns or prices["Volume"].dropna().empty:
        return {"volume_last": None, "volume_20d_avg": None, "volume_vs_avg_x": None}
    vol = prices["Volume"].astype(float)
    last = float(vol.iloc[-1])
    avg_window = vol.tail(_VOLUME_AVG_DAYS)
    avg = float(avg_window.mean()) if not avg_window.empty else None
    ratio = float(last / avg) if avg else None
    return {
        "volume_last": round(last, 2),
        "volume_20d_avg": round(avg, 2) if avg is not None else None,
        "volume_vs_avg_x": round(ratio, 3) if ratio is not None else None,
    }


def _serialize_signal_history(history: list[SignalRecord] | None) -> list[dict[str, Any]]:
    if not history:
        return []
    return [
        {
            "generated_at": h.generated_at.astimezone(timezone.utc).isoformat(),
            "signal_type": h.signal_type,
            "confidence": float(h.confidence),
        }
        for h in history
    ]


def _pnl(
    quantity: float | None, avg_buy: float | None, current_price: float
) -> tuple[float | None, float | None, float | None, float | None]:
    """Return (cost_basis, current_value, pnl, pnl_pct) — all None for watchlist.

    All monetary values are in the holding's currency; this function does no FX.
    """
    if quantity is None or avg_buy is None:
        return None, None, None, None
    cost_basis = quantity * avg_buy
    current_value = quantity * current_price
    pnl = current_value - cost_basis
    pct = (current_value / cost_basis - 1.0) * 100.0 if cost_basis else None
    return (
        round(cost_basis, 2),
        round(current_value, 2),
        round(pnl, 2),
        round(pct, 2) if pct is not None else None,
    )


def _days_since(d: date | datetime | None) -> int | None:
    if d is None:
        return None
    today = datetime.now(timezone.utc).date()
    target = d.date() if isinstance(d, datetime) else d
    return (today - target).days


def build_holding_section(
    holding: Holding,
    prices: pd.DataFrame,
    indicators: Indicators,
    last_earnings_date: date | datetime | None = None,
    signal_history: list[SignalRecord] | None = None,
) -> dict[str, Any]:
    closes = prices["Close"].astype(float).tail(_RECENT_CLOSES).tolist()
    current_price = float(prices["Close"].astype(float).iloc[-1])

    cost_basis, current_value, pnl, pnl_pct = _pnl(
        holding.quantity, holding.avg_buy_price, current_price
    )

    ind = asdict(indicators)
    ind["macd_histogram"] = _macd_histogram(indicators)
    ind["golden_cross"] = _golden_cross(indicators)
    ind["death_cross"] = _death_cross(indicators)
    ind["atr_pct_of_price"] = _atr_pct_of_price(indicators)

    section: dict[str, Any] = {
        "ticker": holding.ticker,
        "name": holding.name,
        "kind": holding.kind,
        "quantity": holding.quantity,
        "avg_buy_price": holding.avg_buy_price,
        "cost_basis": cost_basis,
        "current_price": current_price,
        "current_value": current_value,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "currency": holding.currency,
        "price_change_30d_pct": indicators.pct_change_30d,
        "recent_closes": [float(c) for c in closes],
        "indicators": ind,
        **_high_low_52w(prices, current_price),
        **_volume_context(prices),
        "last_earnings_date": (
            (
                last_earnings_date.date()
                if isinstance(last_earnings_date, datetime)
                else last_earnings_date
            ).isoformat()
            if last_earnings_date is not None
            else None
        ),
        "days_since_earnings": _days_since(last_earnings_date),
        "signal_history": _serialize_signal_history(signal_history),
    }
    return section


def build_brief(
    run_id: UUID,
    started_at: datetime,
    profile_sections: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "started_at": started_at.astimezone(timezone.utc).isoformat(),
        "profiles": profile_sections,
    }


def build_profile_section(profile: Profile, holdings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": str(profile.id),
        "slug": profile.slug,
        "name": profile.name,
        "discord_webhook_url": profile.discord_webhook_url,
        "holdings": holdings,
    }
