"""Build the analysis brief — the JSON contract between `prepare` and the agent."""

from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import pandas as pd

from .models import (
    AnalystConsensus,
    EarningsImpliedMove,
    Fundamentals,
    Holding,
    Indicators,
    InsiderActivity,
    Profile,
    RealtimeQuote,
    SignalRecord,
)

DEFAULT_BRIEF_PATH = "/tmp/stock-analysis-brief.json"

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
    out: list[dict[str, Any]] = []
    for h in history:
        item: dict[str, Any] = {
            "generated_at": h.generated_at.astimezone(timezone.utc).isoformat(),
            "signal_type": h.signal_type,
            "confidence": float(h.confidence),
        }
        if h.outcome_t5_pct is not None:
            item["outcome_t5_pct"] = float(h.outcome_t5_pct)
        if h.outcome_t30_pct is not None:
            item["outcome_t30_pct"] = float(h.outcome_t30_pct)
        out.append(item)
    return out


_FUNDAMENTAL_KEYS: tuple[str, ...] = (
    "trailing_pe",
    "forward_pe",
    "peg_ratio",
    "price_to_book",
    "ev_to_ebitda",
    "dividend_yield_pct",
    "market_cap",
    "debt_to_equity",
    "profit_margin_pct",
    "roe_pct",
    "fcf_yield_pct",
)

_INSIDER_KEYS: tuple[str, ...] = (
    "net_dollars_90d",
    "buy_count_90d",
    "sell_count_90d",
    "net_share_pct",
)


def _fundamentals_block(f: Fundamentals | None) -> dict[str, Any] | None:
    if f is None:
        return None
    block = {k: getattr(f, k) for k in _FUNDAMENTAL_KEYS}
    return block if any(v is not None for v in block.values()) else None


def _insider_block(i: InsiderActivity | None) -> dict[str, Any] | None:
    if i is None:
        return None
    block = {k: getattr(i, k) for k in _INSIDER_KEYS}
    return block if any(v is not None for v in block.values()) else None


def _implied_move_block(m: EarningsImpliedMove | None) -> dict[str, Any] | None:
    if m is None:
        return None
    block = {
        "implied_move_pct": m.implied_move_pct,
        "expiration_date": m.expiration_date.isoformat() if m.expiration_date else None,
        "atm_call_iv": m.atm_call_iv,
        "atm_put_iv": m.atm_put_iv,
    }
    return block if any(v is not None for v in block.values()) else None


def _realtime_fields(rt: RealtimeQuote | None) -> dict[str, Any]:
    if rt is None:
        return {
            "intraday_price": None,
            "intraday_change_pct": None,
            "pre_market_price": None,
            "pre_market_change_pct": None,
            "market_state": None,
        }
    return {
        "intraday_price": rt.intraday_price,
        "intraday_change_pct": rt.intraday_change_pct,
        "pre_market_price": rt.pre_market_price,
        "pre_market_change_pct": rt.pre_market_change_pct,
        "market_state": rt.market_state,
    }


def _analyst_fields(ac: AnalystConsensus | None, current_price: float) -> dict[str, Any]:
    if ac is None:
        return {
            "analyst_target_mean": None,
            "analyst_target_distance_pct": None,
            "analyst_target_high": None,
            "analyst_target_low": None,
            "analyst_recommendation_key": None,
            "analyst_count": None,
        }
    distance = (
        round((ac.target_mean / current_price - 1.0) * 100.0, 2)
        if ac.target_mean is not None and current_price
        else None
    )
    return {
        "analyst_target_mean": ac.target_mean,
        "analyst_target_distance_pct": distance,
        "analyst_target_high": ac.target_high,
        "analyst_target_low": ac.target_low,
        "analyst_recommendation_key": ac.recommendation_key,
        "analyst_count": ac.analyst_count,
    }


def _relative_strength_fields(rs: dict | None) -> dict[str, Any]:
    if rs is None:
        return {
            "baseline_index": None,
            "baseline_pct_change_30d": None,
            "relative_strength_30d_pct": None,
        }
    out: dict[str, Any] = {
        "baseline_index": rs.get("baseline_index"),
        "baseline_pct_change_30d": rs.get("baseline_pct_change_30d"),
        "relative_strength_30d_pct": rs.get("relative_strength_30d_pct"),
    }
    # Sector-ETF relative strength is optional — only emit when run_analysis
    # supplied a mapping for this ticker, otherwise the keys stay absent.
    if "sector_benchmark" in rs:
        out["sector_benchmark"] = rs.get("sector_benchmark")
        out["sector_pct_change_30d"] = rs.get("sector_pct_change_30d")
        out["sector_relative_strength_30d_pct"] = rs.get("sector_relative_strength_30d_pct")
    return out


def _days_until(d: date | datetime | None) -> int | None:
    if d is None:
        return None
    today = datetime.now(timezone.utc).date()
    target = d.date() if isinstance(d, datetime) else d
    delta = (target - today).days
    return delta if delta >= 0 else None


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


def _date_iso(d: date | datetime | None) -> str | None:
    if d is None:
        return None
    return (d.date() if isinstance(d, datetime) else d).isoformat()


def build_holding_section(
    holding: Holding,
    prices: pd.DataFrame,
    indicators: Indicators,
    last_earnings_date: date | datetime | None = None,
    next_earnings_date: date | datetime | None = None,
    signal_history: list[SignalRecord] | None = None,
    realtime: RealtimeQuote | None = None,
    analyst: AnalystConsensus | None = None,
    relative_strength: dict | None = None,
    fundamentals: Fundamentals | None = None,
    insider: InsiderActivity | None = None,
    implied_move: EarningsImpliedMove | None = None,
    position_weight_pct: float | None = None,
) -> dict[str, Any]:
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
        "indicators": ind,
        **_high_low_52w(prices, current_price),
        **_volume_context(prices),
        "last_earnings_date": _date_iso(last_earnings_date),
        "days_since_earnings": _days_since(last_earnings_date),
        "next_earnings_date": _date_iso(next_earnings_date),
        "days_until_earnings": _days_until(next_earnings_date),
        "signal_history": _serialize_signal_history(signal_history),
        **_realtime_fields(realtime),
        **_analyst_fields(analyst, current_price),
        **_relative_strength_fields(relative_strength),
        "fundamentals": _fundamentals_block(fundamentals),
        "insider": _insider_block(insider),
        "earnings_implied_move": _implied_move_block(implied_move),
        "position_weight_pct": (
            round(position_weight_pct, 2) if position_weight_pct is not None else None
        ),
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


def build_profile_section(
    profile: Profile,
    holdings: list[dict[str, Any]],
    portfolio_totals: dict[str, dict[str, Any]] | None = None,
    fx_rates: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(profile.id),
        "slug": profile.slug,
        "name": profile.name,
        "discord_webhook_url": profile.discord_webhook_url,
        "holdings": holdings,
        "portfolio_totals": portfolio_totals or {},
        "fx_rates": fx_rates or {},
    }
