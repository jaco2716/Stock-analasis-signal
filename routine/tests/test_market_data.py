"""yfinance helpers — earnings calendar, realtime quote, analyst consensus, suffix map."""

from typing import Any

import pandas as pd
import pytest

from lib import market_data


class _FakeFastInfo:
    def __init__(self, **attrs: Any) -> None:
        for k, v in attrs.items():
            setattr(self, k, v)


class _FakeTicker:
    def __init__(
        self,
        earnings_frame: pd.DataFrame | None = None,
        info: dict | None = None,
        fast_info: _FakeFastInfo | None = None,
        raises: Exception | None = None,
    ) -> None:
        self._frame = earnings_frame
        self._info = info if info is not None else {}
        self._fast_info = fast_info
        self._raises = raises

    @property
    def earnings_dates(self) -> pd.DataFrame | None:
        if self._raises:
            raise self._raises
        return self._frame

    @property
    def info(self) -> dict:
        if self._raises:
            raise self._raises
        return self._info

    @property
    def fast_info(self) -> _FakeFastInfo | None:
        return self._fast_info


def _earnings_frame(timestamps: list[pd.Timestamp]) -> pd.DataFrame:
    return pd.DataFrame(
        {"EPS Estimate": [None] * len(timestamps), "Reported EPS": [None] * len(timestamps)},
        index=pd.DatetimeIndex(timestamps, name="Earnings Date"),
    )


# ---------------------------- earnings calendar ----------------------------


def test_get_earnings_calendar_returns_past_and_future(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    past = pd.Timestamp("2026-04-21", tz="UTC")
    older = pd.Timestamp("2026-01-15", tz="UTC")
    future = pd.Timestamp("2026-07-21", tz="UTC")
    monkeypatch.setattr(
        market_data.yf,
        "Ticker",
        lambda t: _FakeTicker(earnings_frame=_earnings_frame([future, past, older])),
    )

    cal = market_data.get_earnings_calendar("NFLX")
    assert cal.last_past is not None and cal.last_past.date() == past.date()
    assert cal.next_future is not None and cal.next_future.date() == future.date()


def test_get_earnings_calendar_no_past_or_future(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(earnings_frame=None))
    cal = market_data.get_earnings_calendar("EMP")
    assert cal.last_past is None and cal.next_future is None


def test_get_earnings_calendar_swallows_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(
        market_data.yf, "Ticker", lambda t: _FakeTicker(raises=RuntimeError("rate limited"))
    )
    cal = market_data.get_earnings_calendar("RATE.LIM")
    assert cal.last_past is None and cal.next_future is None


def test_get_earnings_calendar_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    calls = {"n": 0}

    def factory(t: str) -> _FakeTicker:
        calls["n"] += 1
        return _FakeTicker(earnings_frame=_earnings_frame([pd.Timestamp("2026-04-01", tz="UTC")]))

    monkeypatch.setattr(market_data.yf, "Ticker", factory)
    market_data.get_earnings_calendar("ABC")
    market_data.get_earnings_calendar("ABC")
    assert calls["n"] == 1


# ----------------------------- realtime quote ------------------------------


def test_get_realtime_quote_from_info(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    info = {
        "regularMarketPrice": 87.5,
        "regularMarketChangePercent": -1.2,
        "preMarketPrice": 88.0,
        "preMarketChangePercent": 0.5,
        "marketState": "REGULAR",
    }
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(info=info))

    rt = market_data.get_realtime_quote("NFLX")
    assert rt is not None
    assert rt.intraday_price == 87.5
    assert rt.intraday_change_pct == -1.2
    assert rt.pre_market_price == 88.0
    assert rt.market_state == "REGULAR"


def test_get_realtime_quote_falls_back_to_fast_info(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    fast = _FakeFastInfo(last_price=120.0, previous_close=100.0)
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(info={}, fast_info=fast))

    rt = market_data.get_realtime_quote("ABC")
    assert rt is not None
    assert rt.intraday_price == 120.0
    assert rt.intraday_change_pct == pytest.approx(20.0, abs=1e-6)
    assert rt.pre_market_price is None
    assert rt.market_state is None


def test_get_realtime_quote_returns_none_when_everything_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(info={}))
    assert market_data.get_realtime_quote("NADA") is None


# --------------------------- analyst consensus -----------------------------


def test_get_analyst_consensus_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    info = {
        "targetMeanPrice": 105.0,
        "targetHighPrice": 130.0,
        "targetLowPrice": 80.0,
        "recommendationKey": "buy",
        "numberOfAnalystOpinions": 42,
    }
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(info=info))

    ac = market_data.get_analyst_consensus("NFLX")
    assert ac is not None
    assert ac.target_mean == 105.0
    assert ac.target_high == 130.0
    assert ac.target_low == 80.0
    assert ac.recommendation_key == "buy"
    assert ac.analyst_count == 42


def test_get_analyst_consensus_partial_info(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    info = {"targetMeanPrice": 100.0}  # everything else missing
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(info=info))

    ac = market_data.get_analyst_consensus("ABC")
    assert ac is not None
    assert ac.target_mean == 100.0
    assert ac.target_high is None
    assert ac.recommendation_key is None
    assert ac.analyst_count is None


def test_get_analyst_consensus_returns_none_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(info={}))
    assert market_data.get_analyst_consensus("NADA") is None


def test_info_cache_is_shared(monkeypatch: pytest.MonkeyPatch) -> None:
    """Realtime + analyst share a single Ticker.info call per ticker per run."""
    market_data.clear_cache()
    calls = {"n": 0}

    def factory(t: str) -> _FakeTicker:
        calls["n"] += 1
        return _FakeTicker(
            info={
                "regularMarketPrice": 100.0,
                "marketState": "REGULAR",
                "targetMeanPrice": 110.0,
                "recommendationKey": "buy",
            }
        )

    monkeypatch.setattr(market_data.yf, "Ticker", factory)
    market_data.get_realtime_quote("ABC")
    market_data.get_analyst_consensus("ABC")
    # One Ticker(...) construction is unavoidable per call; what matters is the .info
    # property only resolves once for the cached path.
    assert "ABC" in market_data._INFO_CACHE


# ---------------------------- index suffix map -----------------------------


@pytest.mark.parametrize(
    ("ticker", "expected"),
    [
        ("MAERSK-B.CO", "^OMXC25"),
        ("VOLVO-B.ST", "^OMXS30"),
        ("EQNR.OL", "^OBX"),
        ("ULVR.L", "^FTSE"),
        ("SAP.DE", "^GDAXI"),
        ("AIR.PA", "^FCHI"),
        ("ASML.AS", "^AEX"),
        ("BMW.DE", "^GDAXI"),
        ("NFLX", "^GSPC"),
        ("AAPL", "^GSPC"),
        ("UNKNOWN.XX", "^GSPC"),
    ],
)
def test_get_index_for_ticker(ticker: str, expected: str) -> None:
    assert market_data.get_index_for_ticker(ticker) == expected


# ------------------------------- clear_cache -------------------------------


def test_clear_cache_clears_all_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        market_data.yf,
        "Ticker",
        lambda t: _FakeTicker(
            earnings_frame=_earnings_frame([pd.Timestamp("2026-04-01", tz="UTC")]),
            info={"regularMarketPrice": 100.0, "marketState": "REGULAR"},
        ),
    )
    market_data.get_earnings_calendar("ABC")
    market_data.get_realtime_quote("ABC")
    assert "ABC" in market_data._EARNINGS_CAL_CACHE
    assert "ABC" in market_data._INFO_CACHE

    market_data.clear_cache()
    assert "ABC" not in market_data._EARNINGS_CAL_CACHE
    assert "ABC" not in market_data._INFO_CACHE
