"""Typed wrappers for all Supabase reads/writes used by the routine."""

import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import UUID, uuid4

from supabase import Client, create_client

from .config import get_settings
from .models import Holding, Profile, RunStatus, Signal, SignalRecord

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)


def get_active_profiles() -> list[Profile]:
    rows = _client().table("profiles").select("*").eq("is_active", True).execute().data or []
    return [
        Profile(
            id=UUID(r["id"]),
            name=r["name"],
            slug=r["slug"],
            discord_webhook_url=r.get("discord_webhook_url"),
            is_active=bool(r["is_active"]),
        )
        for r in rows
    ]


def get_profile(profile_id: UUID) -> Profile:
    row = (
        _client()
        .table("profiles")
        .select("*")
        .eq("id", str(profile_id))
        .single()
        .execute()
        .data
    )
    if not row:
        raise ValueError(f"profile {profile_id} not found")
    return Profile(
        id=UUID(row["id"]),
        name=row["name"],
        slug=row["slug"],
        discord_webhook_url=row.get("discord_webhook_url"),
        is_active=bool(row["is_active"]),
    )


def get_holdings(profile_id: UUID) -> list[Holding]:
    rows = (
        _client()
        .table("portfolio_holdings")
        .select("*")
        .eq("profile_id", str(profile_id))
        .execute()
        .data
        or []
    )
    return [
        Holding(
            id=UUID(r["id"]),
            profile_id=UUID(r["profile_id"]),
            ticker=r["ticker"],
            name=r["name"],
            quantity=float(r["quantity"]) if r.get("quantity") is not None else None,
            avg_buy_price=(
                float(r["avg_buy_price"])
                if r.get("avg_buy_price") is not None
                else None
            ),
            currency=(r.get("currency") or "DKK").upper(),
            kind=r["kind"],
        )
        for r in rows
    ]


def start_run() -> UUID:
    run_id = uuid4()
    _client().table("analysis_runs").insert(
        {
            "id": str(run_id),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "profile_count": 0,
            "signal_count": 0,
        }
    ).execute()
    return run_id


def finish_run(
    run_id: UUID,
    status: RunStatus,
    profile_count: int,
    signal_count: int,
    error: str | None = None,
) -> None:
    _client().table("analysis_runs").update(
        {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "profile_count": profile_count,
            "signal_count": signal_count,
            "error_message": error,
        }
    ).eq("id", str(run_id)).execute()


_SIGNAL_SELECT = (
    "id, profile_id, ticker, signal_type, confidence, generated_at, run_id, "
    "outcome_t5_pct, outcome_t30_pct, price_at_signal, currency"
)


def _parse_signal_row(r: dict) -> SignalRecord:
    return SignalRecord(
        id=UUID(r["id"]) if r.get("id") else None,
        ticker=r["ticker"],
        signal_type=r["signal_type"],
        confidence=float(r["confidence"]),
        generated_at=datetime.fromisoformat(r["generated_at"].replace("Z", "+00:00")),
        run_id=UUID(r["run_id"]) if r.get("run_id") else None,
        outcome_t5_pct=float(r["outcome_t5_pct"]) if r.get("outcome_t5_pct") is not None else None,
        outcome_t30_pct=(
            float(r["outcome_t30_pct"]) if r.get("outcome_t30_pct") is not None else None
        ),
        price_at_signal=(
            float(r["price_at_signal"]) if r.get("price_at_signal") is not None else None
        ),
        currency=r.get("currency"),
        profile_id=UUID(r["profile_id"]) if r.get("profile_id") else None,
    )


def get_recent_signals_for_holdings(
    profile_id: UUID,
    tickers: list[str],
    per_ticker_limit: int = 5,
) -> dict[str, list[SignalRecord]]:
    """Newest-first signal history per ticker for the given profile.

    One round-trip; we slice to per_ticker_limit per ticker in Python.
    """
    if not tickers:
        return {}
    rows = (
        _client()
        .table("signals")
        .select(_SIGNAL_SELECT)
        .eq("profile_id", str(profile_id))
        .in_("ticker", tickers)
        .order("generated_at", desc=True)
        .limit(per_ticker_limit * len(tickers))
        .execute()
        .data
        or []
    )
    grouped: dict[str, list[SignalRecord]] = {t: [] for t in tickers}
    for r in rows:
        ticker = r["ticker"]
        bucket = grouped.setdefault(ticker, [])
        if len(bucket) >= per_ticker_limit:
            continue
        bucket.append(_parse_signal_row(r))
    return grouped


def get_signals_needing_outcome(window_days: int, batch: int = 200) -> list[SignalRecord]:
    """Signals older than `window_days` whose T+window outcome is not yet computed."""
    if window_days not in (5, 30):
        raise ValueError(f"window_days must be 5 or 30, got {window_days}")
    column = f"outcome_t{window_days}_pct"
    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    rows = (
        _client()
        .table("signals")
        .select(_SIGNAL_SELECT)
        .is_(column, "null")
        .lt("generated_at", cutoff)
        .order("generated_at", desc=False)
        .limit(batch)
        .execute()
        .data
        or []
    )
    return [_parse_signal_row(r) for r in rows]


def update_signal_outcome(signal_id: UUID, window_days: int, outcome_pct: float) -> None:
    if window_days not in (5, 30):
        raise ValueError(f"window_days must be 5 or 30, got {window_days}")
    column = f"outcome_t{window_days}_pct"
    _client().table("signals").update(
        {
            column: round(float(outcome_pct), 2),
            "outcome_computed_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", str(signal_id)).execute()


def insert_signal(signal: Signal) -> None:
    if signal.profile_id is None or signal.run_id is None:
        raise ValueError("signal.profile_id and signal.run_id must be set before insert")
    _client().table("signals").insert(
        {
            "profile_id": str(signal.profile_id),
            "run_id": str(signal.run_id),
            "ticker": signal.ticker,
            "signal_type": signal.signal_type,
            "reasoning": signal.reasoning,
            "confidence": signal.confidence,
            "generated_at": signal.generated_at.isoformat(),
            "price_at_signal": signal.price_at_signal,
            "currency": signal.currency,
        }
    ).execute()


def get_signals_needing_price(batch: int = 200) -> list[SignalRecord]:
    """Signals missing price_at_signal, oldest first so backfill is deterministic."""
    rows = (
        _client()
        .table("signals")
        .select(_SIGNAL_SELECT)
        .is_("price_at_signal", "null")
        .order("generated_at", desc=False)
        .limit(batch)
        .execute()
        .data
        or []
    )
    return [_parse_signal_row(r) for r in rows]


def get_holding_currency(profile_id: UUID, ticker: str) -> str | None:
    """Look up the currency on a portfolio_holdings row; None if no match."""
    rows = (
        _client()
        .table("portfolio_holdings")
        .select("currency")
        .eq("profile_id", str(profile_id))
        .eq("ticker", ticker)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return None
    cur = rows[0].get("currency")
    return cur.upper() if isinstance(cur, str) else None


def update_signal_price(signal_id: UUID, price_at_signal: float, currency: str) -> None:
    _client().table("signals").update(
        {
            "price_at_signal": round(float(price_at_signal), 6),
            "currency": currency,
        }
    ).eq("id", str(signal_id)).execute()
