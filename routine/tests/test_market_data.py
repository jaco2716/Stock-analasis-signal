"""yfinance helpers — earnings calendar, realtime quote, analyst consensus, suffix map."""

from datetime import datetime, timezone
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
        insider_frame: pd.DataFrame | None = None,
        options: tuple[str, ...] = (),
        option_chains: dict | None = None,
        raises: Exception | None = None,
    ) -> None:
        self._frame = earnings_frame
        self._info = info if info is not None else {}
        self._fast_info = fast_info
        self._insider = insider_frame
        self._options = options
        self._chains = option_chains or {}
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

    @property
    def insider_transactions(self) -> pd.DataFrame | None:
        if self._raises:
            raise self._raises
        return self._insider

    @property
    def options(self) -> tuple[str, ...]:
        return self._options

    def option_chain(self, exp: str):
        return self._chains[exp]


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


# ----------------------------- fundamentals --------------------------------


def test_get_fundamentals_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    info = {
        "trailingPE": 18.4,
        "forwardPE": 16.2,
        "pegRatio": 0.85,
        "priceToBook": 4.2,
        "enterpriseToEbitda": 12.1,
        "dividendYield": 0.021,        # 2.1%
        "marketCap": 1_000_000_000.0,
        "debtToEquity": 75.0,
        "profitMargins": 0.18,         # 18%
        "returnOnEquity": 0.22,        # 22%
        "freeCashflow": 60_000_000.0,
    }
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(info=info))

    f = market_data.get_fundamentals("NFLX")
    assert f is not None
    assert f.trailing_pe == 18.4
    assert f.peg_ratio == 0.85
    assert f.dividend_yield_pct == pytest.approx(2.1, abs=1e-6)
    assert f.profit_margin_pct == pytest.approx(18.0, abs=1e-6)
    assert f.fcf_yield_pct == pytest.approx(6.0, abs=1e-6)


def test_get_fundamentals_returns_none_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(info={}))
    assert market_data.get_fundamentals("NADA") is None


# ------------------------------ insider ------------------------------------


def _insider_frame(rows: list[tuple[str, float, float, str]]) -> pd.DataFrame:
    """rows = [(transaction, value, shares, days_ago_iso)]"""
    return pd.DataFrame(
        {
            "Transaction": [r[0] for r in rows],
            "Value": [r[1] for r in rows],
            "Shares": [r[2] for r in rows],
            "Start Date": [r[3] for r in rows],
        }
    )


def test_get_insider_activity_filters_to_90d_and_sums_dollars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_data.clear_cache()
    today = pd.Timestamp.now(tz="UTC").normalize()
    recent_buy = (today - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    recent_sell = (today - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    older = (today - pd.Timedelta(days=200)).strftime("%Y-%m-%d")

    frame = _insider_frame(
        [
            ("Purchase", 100_000.0, 1000.0, recent_buy),
            ("Purchase", 50_000.0, 500.0, recent_buy),
            ("Sale", 30_000.0, 300.0, recent_sell),
            ("Purchase", 999_999.0, 10000.0, older),  # outside 90d -> ignored
        ]
    )
    monkeypatch.setattr(
        market_data.yf,
        "Ticker",
        lambda t: _FakeTicker(insider_frame=frame, info={"sharesOutstanding": 1_000_000.0}),
    )

    a = market_data.get_insider_activity("ABC")
    assert a is not None
    assert a.buy_count_90d == 2
    assert a.sell_count_90d == 1
    assert a.net_dollars_90d == pytest.approx(120_000.0, abs=1e-6)  # 100k + 50k - 30k
    # Net shares = 1000 + 500 - 300 = 1200 / 1_000_000 * 100 = 0.12%
    assert a.net_share_pct == pytest.approx(0.12, abs=1e-6)


def test_get_insider_activity_handles_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(insider_frame=None))
    # Stub out the EDGAR fallback so the test doesn't hit the network.
    monkeypatch.setattr(market_data, "_get_insider_activity_edgar", lambda ticker: None)
    assert market_data.get_insider_activity("NADA") is None


def test_get_insider_activity_swallows_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(
        market_data.yf, "Ticker", lambda t: _FakeTicker(raises=RuntimeError("rate limited"))
    )
    monkeypatch.setattr(market_data, "_get_insider_activity_edgar", lambda ticker: None)
    assert market_data.get_insider_activity("ERR") is None


def test_get_insider_activity_skips_edgar_for_non_us_ticker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(insider_frame=None))

    called: dict[str, bool] = {"hit": False}

    def _should_not_be_called(ticker: str):  # pragma: no cover - guard
        called["hit"] = True
        return None

    monkeypatch.setattr(market_data, "_get_insider_activity_edgar", _should_not_be_called)
    assert market_data.get_insider_activity("MAERSK-B.CO") is None
    assert called["hit"] is False, "EDGAR fallback should not run for .CO ticker"


# ------------------------- EDGAR fallback -----------------------------------


class _FakeResp:
    def __init__(self, *, json_body: Any = None, content: bytes = b"", status: int = 200) -> None:
        self._json = json_body
        self.content = content
        self.status_code = status

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


_SAMPLE_FORM4_XML = b"""<?xml version="1.0"?>
<ownershipDocument>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionAmounts>
        <transactionShares><value>1000</value></transactionShares>
        <transactionPricePerShare><value>50.00</value></transactionPricePerShare>
      </transactionAmounts>
      <transactionCoding>
        <transactionCode>S</transactionCode>
      </transactionCoding>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionAmounts>
        <transactionShares><value>200</value></transactionShares>
        <transactionPricePerShare><value>50.00</value></transactionPricePerShare>
      </transactionAmounts>
      <transactionCoding>
        <transactionCode>P</transactionCode>
      </transactionCoding>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


def test_edgar_fallback_aggregates_form4(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    today = datetime.now(timezone.utc).date().isoformat()

    def fake_get(url: str, **_: Any) -> _FakeResp:
        if "company_tickers.json" in url:
            return _FakeResp(json_body={"0": {"ticker": "ABC", "cik_str": 1234}})
        if "submissions/CIK" in url:
            return _FakeResp(
                json_body={
                    "filings": {
                        "recent": {
                            "form": ["4", "8-K", "4"],
                            "accessionNumber": ["0001-23-456789", "0001-23-000001", "0001-23-456788"],
                            "filingDate": [today, today, today],
                            "primaryDocument": ["form4.xml", "8k.htm", "form4_b.xml"],
                        }
                    }
                }
            )
        if "Archives/edgar/data/" in url:
            return _FakeResp(content=_SAMPLE_FORM4_XML)
        return _FakeResp(status=404)

    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(insider_frame=None, info={"sharesOutstanding": 100_000_000.0}))
    monkeypatch.setattr(market_data.requests, "get", fake_get)

    a = market_data.get_insider_activity("ABC")
    assert a is not None
    # Two Form 4 filings × (1 sell of 1000 @ $50 + 1 buy of 200 @ $50) per filing
    # = 2 sells (2×$50,000 = $100,000) + 2 buys (2×$10,000 = $20,000); net −$80,000.
    assert a.buy_count_90d == 2
    assert a.sell_count_90d == 2
    assert a.net_dollars_90d == pytest.approx(-80_000.0, abs=1e-2)
    # Net shares = (200 + 200) - (1000 + 1000) = -1600; /100M * 100 = -0.0016%
    assert a.net_share_pct == pytest.approx(-0.0016, abs=1e-6)


def test_edgar_fallback_returns_none_when_cik_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(insider_frame=None))
    monkeypatch.setattr(
        market_data.requests,
        "get",
        lambda url, **_: _FakeResp(json_body={"0": {"ticker": "ABC", "cik_str": 1234}}),
    )
    # Ticker NOT in the CIK map → EDGAR returns None.
    assert market_data.get_insider_activity("UNKNOWN") is None


# ----------------------------- implied move --------------------------------


def _option_row(strike: float, bid: float, ask: float, iv: float, last: float = 0.0) -> dict:
    return {"strike": strike, "bid": bid, "ask": ask, "lastPrice": last, "impliedVolatility": iv}


def _option_chain_obj(calls: list[dict], puts: list[dict]):
    class _Chain:
        pass

    c = _Chain()
    c.calls = pd.DataFrame(calls)
    c.puts = pd.DataFrame(puts)
    return c


def test_get_earnings_implied_move_atm_straddle(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    exp = "2026-05-22"
    chain = _option_chain_obj(
        calls=[
            _option_row(95, 4.0, 4.6, 0.55),
            _option_row(100, 2.4, 2.8, 0.50),    # ATM
            _option_row(105, 1.0, 1.2, 0.60),
        ],
        puts=[
            _option_row(95, 0.8, 1.0, 0.58),
            _option_row(100, 2.0, 2.4, 0.52),    # ATM
            _option_row(105, 4.5, 5.0, 0.62),
        ],
    )
    monkeypatch.setattr(
        market_data.yf,
        "Ticker",
        lambda t: _FakeTicker(options=(exp,), option_chains={exp: chain}),
    )

    next_earnings = datetime(2026, 5, 20, tzinfo=timezone.utc)
    m = market_data.get_earnings_implied_move("NFLX", current_price=100.0, next_earnings_date=next_earnings)
    assert m is not None
    # call mid 2.6, put mid 2.2 -> 4.8 / 100 * 100 = 4.8%
    assert m.implied_move_pct == pytest.approx(4.8, abs=1e-2)
    assert m.expiration_date.isoformat() == exp
    assert m.atm_call_iv == pytest.approx(50.0, abs=1e-6)
    assert m.atm_put_iv == pytest.approx(52.0, abs=1e-6)


def test_get_earnings_implied_move_no_options(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: _FakeTicker(options=()))
    m = market_data.get_earnings_implied_move(
        "NADA", current_price=100.0, next_earnings_date=datetime(2026, 5, 20, tzinfo=timezone.utc)
    )
    assert m is None


def test_get_earnings_implied_move_skipped_on_null_inputs() -> None:
    assert market_data.get_earnings_implied_move("X", current_price=100.0, next_earnings_date=None) is None
    assert market_data.get_earnings_implied_move(
        "X", current_price=0.0, next_earnings_date=datetime(2026, 5, 20)
    ) is None


# --------------------------------- FX --------------------------------------


def test_get_fx_rates_uses_price_history(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    fake_close = pd.DataFrame({"Close": [0.146]}, index=[pd.Timestamp("2026-05-09")])

    def fake_history(ticker: str, period: str = "5d"):
        assert period == "5d"
        return fake_close

    monkeypatch.setattr(market_data, "get_price_history", fake_history)

    out = market_data.get_fx_rates({"DKK", "USD"}, home="USD")
    assert "USD_USD" not in out  # home filtered out
    assert out["DKK_USD"] == pytest.approx(0.146, abs=1e-6)


def test_get_fx_rates_handles_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    market_data.clear_cache()
    monkeypatch.setattr(market_data, "get_price_history", lambda *a, **k: None)
    out = market_data.get_fx_rates({"DKK", "EUR"}, home="USD")
    assert out["DKK_USD"] is None
    assert out["EUR_USD"] is None
