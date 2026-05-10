"""yfinance helpers — earnings date lookup with monkeypatched Ticker."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from lib import market_data


class _FakeTicker:
    def __init__(self, frame: pd.DataFrame | None = None, raises: Exception | None = None):
        self._frame = frame
        self._raises = raises

    @property
    def earnings_dates(self) -> pd.DataFrame | None:
        if self._raises:
            raise self._raises
        return self._frame


def _frame(timestamps: list[pd.Timestamp]) -> pd.DataFrame:
    return pd.DataFrame(
        {"EPS Estimate": [None] * len(timestamps), "Reported EPS": [None] * len(timestamps)},
        index=pd.DatetimeIndex(timestamps, name="Earnings Date"),
    )


def test_get_last_earnings_date_returns_most_recent_past(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    past = pd.Timestamp("2026-04-21", tz="UTC")
    older = pd.Timestamp("2026-01-15", tz="UTC")
    future = pd.Timestamp("2026-07-21", tz="UTC")
    monkeypatch.setattr(
        market_data.yf, "Ticker", lambda t: _FakeTicker(_frame([future, past, older]))
    )

    got = market_data.get_last_earnings_date("NFLX")
    assert got is not None
    assert got.date() == past.date()


def test_get_last_earnings_date_handles_no_past_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(
        market_data.yf,
        "Ticker",
        lambda t: _FakeTicker(_frame([pd.Timestamp("2099-01-01", tz="UTC")])),
    )
    assert market_data.get_last_earnings_date("FUT") is None


def test_get_last_earnings_date_swallows_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(
        market_data.yf, "Ticker", lambda t: _FakeTicker(raises=RuntimeError("rate limited"))
    )
    assert market_data.get_last_earnings_date("RATE.LIM") is None


def test_get_last_earnings_date_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    calls = {"n": 0}

    def factory(t: str) -> _FakeTicker:
        calls["n"] += 1
        return _FakeTicker(_frame([pd.Timestamp("2026-04-01", tz="UTC")]))

    monkeypatch.setattr(market_data.yf, "Ticker", factory)
    market_data.get_last_earnings_date("ABC")
    market_data.get_last_earnings_date("ABC")
    assert calls["n"] == 1


def test_clear_cache_clears_earnings(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(
        market_data.yf, "Ticker", lambda t: _FakeTicker(_frame([pd.Timestamp("2026-04-01", tz="UTC")]))
    )
    market_data.get_last_earnings_date("ABC")
    assert "ABC" in market_data._EARNINGS_CACHE
    market_data.clear_cache()
    assert "ABC" not in market_data._EARNINGS_CACHE
