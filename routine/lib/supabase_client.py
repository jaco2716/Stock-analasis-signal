"""Typed wrappers for all Supabase reads/writes used by the routine."""

import logging
from datetime import datetime, timezone
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
        .select("ticker, signal_type, confidence, generated_at, run_id")
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
        bucket.append(
            SignalRecord(
                ticker=ticker,
                signal_type=r["signal_type"],
                confidence=float(r["confidence"]),
                generated_at=datetime.fromisoformat(r["generated_at"].replace("Z", "+00:00")),
                run_id=UUID(r["run_id"]) if r.get("run_id") else None,
            )
        )
    return grouped


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
        }
    ).execute()
