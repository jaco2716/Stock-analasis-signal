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


def build_holding_section(
    holding: Holding, prices: pd.DataFrame, indicators: Indicators
) -> dict[str, Any]:
    closes = prices["Close"].astype(float).tail(_RECENT_CLOSES).tolist()
    ind = asdict(indicators)
    ind["macd_histogram"] = _macd_histogram(indicators)
    ind["golden_cross"] = _golden_cross(indicators)
    ind["death_cross"] = _death_cross(indicators)
    return {
        "ticker": holding.ticker,
        "name": holding.name,
        "kind": holding.kind,
        "position_dkk": holding.position_dkk,
        "current_price": float(prices["Close"].astype(float).iloc[-1]),
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
