"""Build the analysis brief — the JSON contract between `prepare` and the agent."""

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pandas as pd

from .models import Holding, Indicators, Profile

DEFAULT_BRIEF_PATH = "/tmp/stock-analysis-brief.json"

_RECENT_CLOSES = 10


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


def _pnl(
    quantity: float | None, avg_buy: float | None, current_price: float
) -> tuple[float | None, float | None, float | None, float | None]:
    """Return (cost_basis_dkk, current_value_dkk, pnl_dkk, pnl_pct) — all None for watchlist."""
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


def build_holding_section(
    holding: Holding, prices: pd.DataFrame, indicators: Indicators
) -> dict[str, Any]:
    closes = prices["Close"].astype(float).tail(_RECENT_CLOSES).tolist()
    current_price = float(prices["Close"].astype(float).iloc[-1])

    cost_basis, current_value, pnl_dkk, pnl_pct = _pnl(
        holding.quantity, holding.avg_buy_price_dkk, current_price
    )

    ind = asdict(indicators)
    ind["macd_histogram"] = _macd_histogram(indicators)
    ind["golden_cross"] = _golden_cross(indicators)
    ind["death_cross"] = _death_cross(indicators)

    return {
        "ticker": holding.ticker,
        "name": holding.name,
        "kind": holding.kind,
        "quantity": holding.quantity,
        "avg_buy_price_dkk": holding.avg_buy_price_dkk,
        "cost_basis_dkk": cost_basis,
        "current_price": current_price,
        "current_value_dkk": current_value,
        "pnl_dkk": pnl_dkk,
        "pnl_pct": pnl_pct,
        "currency": "DKK",
        "price_change_30d_pct": indicators.pct_change_30d,
        "recent_closes": [float(c) for c in closes],
        "indicators": ind,
    }


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
