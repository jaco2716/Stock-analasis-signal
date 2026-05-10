"""score-signals subcommand: backfills T+5 / T+30 returns onto past signals."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pandas as pd
import pytest

import run_analysis
from lib import market_data, supabase_client
from lib.models import SignalRecord


def _signal(days_ago: int) -> SignalRecord:
    return SignalRecord(
        id=uuid4(),
        ticker="ABC",
        signal_type="BUY",
        confidence=0.7,
        generated_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        run_id=uuid4(),
    )


def _price_frame(rows: int = 60) -> pd.DataFrame:
    """Synthetic daily closes: linear ramp 100 -> 100+rows."""
    closes = [100.0 + i for i in range(rows)]
    idx = pd.bdate_range(end=pd.Timestamp.now("UTC").normalize() + pd.Timedelta(days=2), periods=rows)
    return pd.DataFrame({"Close": closes}, index=idx)


def test_score_signals_dispatches_and_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    sig = _signal(days_ago=10)

    def fake_get_pending(window_days: int, batch: int = 200):
        if window_days == 5:
            return [sig]
        return []

    updates: list[tuple[UUID, int, float]] = []

    def fake_update(signal_id: UUID, window_days: int, outcome_pct: float) -> None:
        updates.append((signal_id, window_days, outcome_pct))

    monkeypatch.setattr(supabase_client, "get_signals_needing_outcome", fake_get_pending)
    monkeypatch.setattr(supabase_client, "update_signal_outcome", fake_update)
    monkeypatch.setattr(market_data, "get_price_history", lambda *a, **k: _price_frame())

    args = run_analysis.build_parser().parse_args(["score-signals", "--window", "5"])
    rc = run_analysis.cmd_score_signals(args)
    assert rc == 0
    assert len(updates) == 1
    assert updates[0][0] == sig.id
    assert updates[0][1] == 5


def test_score_signals_dry_run_skips_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    sig = _signal(days_ago=10)
    monkeypatch.setattr(
        supabase_client,
        "get_signals_needing_outcome",
        lambda window_days, batch=200: [sig] if window_days == 5 else [],
    )
    called = {"n": 0}
    monkeypatch.setattr(
        supabase_client,
        "update_signal_outcome",
        lambda *a, **k: called.__setitem__("n", called["n"] + 1),
    )
    monkeypatch.setattr(market_data, "get_price_history", lambda *a, **k: _price_frame())

    args = run_analysis.build_parser().parse_args(
        ["score-signals", "--window", "5", "--dry-run"]
    )
    run_analysis.cmd_score_signals(args)
    assert called["n"] == 0


def test_score_signals_skips_when_no_price_data(monkeypatch: pytest.MonkeyPatch) -> None:
    sig = _signal(days_ago=10)
    monkeypatch.setattr(
        supabase_client,
        "get_signals_needing_outcome",
        lambda window_days, batch=200: [sig] if window_days == 5 else [],
    )
    updates: list = []
    monkeypatch.setattr(
        supabase_client,
        "update_signal_outcome",
        lambda *a, **k: updates.append(a),
    )
    monkeypatch.setattr(market_data, "get_price_history", lambda *a, **k: None)

    args = run_analysis.build_parser().parse_args(["score-signals", "--window", "5"])
    run_analysis.cmd_score_signals(args)
    assert updates == []


def test_score_signals_both_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    s_recent = _signal(days_ago=10)
    s_old = _signal(days_ago=40)

    def fake_get_pending(window_days: int, batch: int = 200):
        if window_days == 5:
            return [s_recent]
        if window_days == 30:
            return [s_old]
        return []

    updates: list[tuple[UUID, int, float]] = []
    monkeypatch.setattr(supabase_client, "get_signals_needing_outcome", fake_get_pending)
    monkeypatch.setattr(
        supabase_client,
        "update_signal_outcome",
        lambda sid, w, p: updates.append((sid, w, p)),
    )
    monkeypatch.setattr(market_data, "get_price_history", lambda *a, **k: _price_frame())

    args = run_analysis.build_parser().parse_args(["score-signals", "--window", "both"])
    run_analysis.cmd_score_signals(args)
    windows = sorted({u[1] for u in updates})
    assert windows == [5, 30]
