"""Read-side tests for the new Supabase wrappers (write paths covered indirectly)."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from lib import supabase_client


class _FakeQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.calls: list[tuple[str, tuple, dict]] = []

    def _record(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        return self

    def select(self, *a, **k): return self._record("select", *a, **k)
    def eq(self, *a, **k): return self._record("eq", *a, **k)
    def in_(self, *a, **k): return self._record("in_", *a, **k)
    def order(self, *a, **k): return self._record("order", *a, **k)
    def limit(self, *a, **k): return self._record("limit", *a, **k)

    def execute(self):
        class _Resp:
            data = self._rows
        return _Resp()


class _FakeClient:
    def __init__(self, rows: list[dict]):
        self.last_table: str | None = None
        self._rows = rows

    def table(self, name: str) -> _FakeQuery:
        self.last_table = name
        return _FakeQuery(self._rows)


def _row(ticker: str, signal_type: str, days_ago: int, confidence: float = 0.5) -> dict:
    ts = datetime(2026, 5, 9, 12, tzinfo=timezone.utc) - timedelta(days=days_ago)
    return {
        "ticker": ticker,
        "signal_type": signal_type,
        "confidence": confidence,
        "generated_at": ts.isoformat(),
        "run_id": str(uuid4()),
    }


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> _FakeClient:
    rows = [
        _row("ABC", "HOLD", 1, 0.6),
        _row("ABC", "BUY", 3, 0.8),
        _row("ABC", "HOLD", 5, 0.5),
        _row("ABC", "HOLD", 7, 0.4),
        _row("ABC", "HOLD", 8, 0.4),
        _row("ABC", "BUY", 9, 0.7),  # 6th — should be sliced off
        _row("XYZ", "SELL", 2, 0.9),
    ]
    client = _FakeClient(rows)
    monkeypatch.setattr(supabase_client, "_client", lambda: client)
    return client


def test_get_recent_signals_groups_and_caps_per_ticker(fake_client: _FakeClient) -> None:
    profile_id = UUID("11111111-1111-1111-1111-111111111111")
    result = supabase_client.get_recent_signals_for_holdings(
        profile_id, ["ABC", "XYZ"], per_ticker_limit=5
    )
    assert set(result) == {"ABC", "XYZ"}
    assert len(result["ABC"]) == 5
    # Newest-first ordering preserved by the order(desc) clause; first row is the most recent.
    assert result["ABC"][0].signal_type == "HOLD"
    assert result["ABC"][0].confidence == 0.6
    assert len(result["XYZ"]) == 1
    assert result["XYZ"][0].signal_type == "SELL"
    assert fake_client.last_table == "signals"


def test_get_recent_signals_empty_tickers_no_query(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"n": 0}
    monkeypatch.setattr(supabase_client, "_client", lambda: called.__setitem__("n", 1))
    result = supabase_client.get_recent_signals_for_holdings(uuid4(), [])
    assert result == {}
    assert called["n"] == 0


def test_get_recent_signals_unseen_ticker_returns_empty_list(fake_client: _FakeClient) -> None:
    result = supabase_client.get_recent_signals_for_holdings(
        uuid4(), ["ABC", "ZZZ"], per_ticker_limit=3
    )
    assert result["ZZZ"] == []
    assert len(result["ABC"]) == 3


# ---------------------- Tier-3: signal-outcome wrappers --------------------


class _FakeUpdateQuery:
    """Minimal fake for the chained update().eq().execute() call shape."""

    def __init__(self, log: list) -> None:
        self.log = log
        self._table: str | None = None
        self._update: dict | None = None
        self._where: dict[str, str] = {}

    def update(self, payload: dict):
        self._update = payload
        return self

    def select(self, *_a, **_k):
        return self

    def is_(self, col: str, _val):
        self._where[col + "_is"] = "null"
        return self

    def lt(self, col: str, val):
        self._where[col + "_lt"] = val
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n: int):
        self._where["limit"] = n
        return self

    def eq(self, col: str, val):
        self._where[col] = val
        return self

    def execute(self):
        self.log.append({"update": self._update, "where": dict(self._where)})

        class _Resp:
            data: list = []

        return _Resp()


class _FakeUpdateClient:
    def __init__(self) -> None:
        self.calls: list = []

    def table(self, name: str) -> _FakeUpdateQuery:
        return _FakeUpdateQuery(self.calls)


def test_update_signal_outcome_writes_correct_column(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeUpdateClient()
    monkeypatch.setattr(supabase_client, "_client", lambda: client)
    sig_id = uuid4()
    supabase_client.update_signal_outcome(sig_id, 5, 3.214)
    assert len(client.calls) == 1
    payload = client.calls[0]["update"]
    assert "outcome_t5_pct" in payload
    assert payload["outcome_t5_pct"] == 3.21
    assert "outcome_computed_at" in payload
    assert client.calls[0]["where"]["id"] == str(sig_id)


def test_update_signal_outcome_rejects_invalid_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supabase_client, "_client", lambda: _FakeUpdateClient())
    with pytest.raises(ValueError):
        supabase_client.update_signal_outcome(uuid4(), 7, 1.0)


def test_get_signals_needing_outcome_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "id": str(uuid4()),
            "ticker": "ABC",
            "signal_type": "BUY",
            "confidence": 0.7,
            "generated_at": "2026-04-01T12:00:00+00:00",
            "run_id": str(uuid4()),
            "outcome_t5_pct": None,
            "outcome_t30_pct": None,
        }
    ]

    class _ReadClient:
        def __init__(self) -> None:
            self.last_filter: dict[str, str] = {}

        def table(self, _: str):
            outer = self

            class _Q(_FakeUpdateQuery):
                def execute(self_inner):
                    outer.last_filter = dict(self_inner._where)

                    class _R:
                        data = rows

                    return _R()

            return _Q(log=[])

    client = _ReadClient()
    monkeypatch.setattr(supabase_client, "_client", lambda: client)

    result = supabase_client.get_signals_needing_outcome(5, batch=10)
    assert len(result) == 1
    assert result[0].ticker == "ABC"
    assert client.last_filter.get("outcome_t5_pct_is") == "null"
    assert "generated_at_lt" in client.last_filter
    assert client.last_filter.get("limit") == 10
