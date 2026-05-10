"""yfinance wrapper with retries and a per-run cache."""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd
import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .models import (
    AnalystConsensus,
    EarningsCalendar,
    EarningsImpliedMove,
    Fundamentals,
    InsiderActivity,
    RealtimeQuote,
)

log = logging.getLogger(__name__)

# Per-run caches; cleared by run_analysis.main before iteration starts.
_CACHE: dict[tuple[str, str], pd.DataFrame] = {}
_EARNINGS_CAL_CACHE: dict[str, EarningsCalendar] = {}
_INFO_CACHE: dict[str, dict[str, Any] | None] = {}
_INSIDER_CACHE: dict[str, InsiderActivity | None] = {}


def clear_cache() -> None:
    _CACHE.clear()
    _EARNINGS_CAL_CACHE.clear()
    _INFO_CACHE.clear()
    _INSIDER_CACHE.clear()


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
)
def _download(ticker: str, period: str) -> pd.DataFrame:
    df = yf.download(
        ticker,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    # yfinance can return a MultiIndex columns frame for single tickers; flatten.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def get_price_history(ticker: str, period: str = "6mo") -> pd.DataFrame | None:
    key = (ticker, period)
    if key in _CACHE:
        return _CACHE[key]
    try:
        df = _download(ticker, period)
    except Exception:
        log.exception("yfinance download failed for %s", ticker)
        return None
    if df is None or df.empty:
        log.warning("empty price frame for %s", ticker)
        return None
    _CACHE[key] = df
    return df


def _get_ticker_info(ticker: str) -> dict[str, Any] | None:
    """Cached `Ticker.info` lookup, shared by realtime + analyst helpers."""
    if ticker in _INFO_CACHE:
        return _INFO_CACHE[ticker]
    info: dict[str, Any] | None = None
    try:
        raw = yf.Ticker(ticker).info or {}
        info = raw if isinstance(raw, dict) else None
    except Exception as e:
        log.warning("Ticker.info lookup failed for %s: %s", ticker, e)
    _INFO_CACHE[ticker] = info
    return info


def _to_utc(ts: pd.Timestamp) -> datetime:
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.to_pydatetime().astimezone(timezone.utc)


def get_earnings_calendar(ticker: str) -> EarningsCalendar:
    """Most recent past + next future earnings dates from yfinance.

    yfinance's `earnings_dates` is flaky for non-US tickers and can raise on rate
    limits, so any failure resolves to nulls rather than aborting the brief.
    """
    if ticker in _EARNINGS_CAL_CACHE:
        return _EARNINGS_CAL_CACHE[ticker]
    last_past: datetime | None = None
    next_future: datetime | None = None
    try:
        df = yf.Ticker(ticker).earnings_dates
        if df is not None and not df.empty:
            now = pd.Timestamp.now(tz="UTC")
            past = df.index[df.index <= now]
            future = df.index[df.index > now]
            if len(past) > 0:
                last_past = _to_utc(past.max())
            if len(future) > 0:
                next_future = _to_utc(future.min())
    except Exception as e:
        log.warning("earnings_dates lookup failed for %s: %s", ticker, e)
    cal = EarningsCalendar(last_past=last_past, next_future=next_future)
    _EARNINGS_CAL_CACHE[ticker] = cal
    return cal


def _f(v: Any) -> float | None:
    """Coerce to float-or-None; treat NaN, missing, or non-numeric as None."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _fast_info_attr(ft: Any, name: str) -> Any:
    try:
        return getattr(ft, name, None)
    except Exception:
        return None


def get_realtime_quote(ticker: str) -> RealtimeQuote | None:
    """Intraday + pre-market snapshot. Falls back to `fast_info` when `info` is empty."""
    info = _get_ticker_info(ticker) or {}

    intraday_price = _f(info.get("regularMarketPrice"))
    intraday_change_pct = _f(info.get("regularMarketChangePercent"))
    pre_market_price = _f(info.get("preMarketPrice"))
    pre_market_change_pct = _f(info.get("preMarketChangePercent"))
    market_state = info.get("marketState") if isinstance(info.get("marketState"), str) else None

    # Fallback: fast_info has lighter, more reliable intraday fields.
    if intraday_price is None or intraday_change_pct is None:
        try:
            ft = yf.Ticker(ticker).fast_info
            if intraday_price is None:
                intraday_price = _f(_fast_info_attr(ft, "last_price"))
            if intraday_change_pct is None:
                last = _f(_fast_info_attr(ft, "last_price"))
                prev = _f(_fast_info_attr(ft, "previous_close"))
                if last is not None and prev:
                    intraday_change_pct = (last - prev) / prev * 100.0
        except Exception as e:
            log.warning("fast_info fallback failed for %s: %s", ticker, e)

    fields = (
        intraday_price,
        intraday_change_pct,
        pre_market_price,
        pre_market_change_pct,
        market_state,
    )
    if all(f is None for f in fields):
        return None
    return RealtimeQuote(
        intraday_price=intraday_price,
        intraday_change_pct=intraday_change_pct,
        pre_market_price=pre_market_price,
        pre_market_change_pct=pre_market_change_pct,
        market_state=market_state,
    )


def get_analyst_consensus(ticker: str) -> AnalystConsensus | None:
    info = _get_ticker_info(ticker) or {}
    target_mean = _f(info.get("targetMeanPrice"))
    target_high = _f(info.get("targetHighPrice"))
    target_low = _f(info.get("targetLowPrice"))
    rec_key = info.get("recommendationKey") if isinstance(info.get("recommendationKey"), str) else None
    count = info.get("numberOfAnalystOpinions")
    analyst_count: int | None = None
    if isinstance(count, (int, float)) and count == count:  # not NaN
        analyst_count = int(count)
    if all(v is None for v in (target_mean, target_high, target_low, rec_key, analyst_count)):
        return None
    return AnalystConsensus(
        target_mean=target_mean,
        target_high=target_high,
        target_low=target_low,
        recommendation_key=rec_key,
        analyst_count=analyst_count,
    )


_INDEX_BY_SUFFIX: dict[str, str] = {
    ".CO": "^OMXC25",   # Copenhagen
    ".ST": "^OMXS30",   # Stockholm
    ".OL": "^OBX",      # Oslo
    ".HE": "^OMXH25",   # Helsinki
    ".L":  "^FTSE",     # London
    ".DE": "^GDAXI",    # Frankfurt
    ".PA": "^FCHI",     # Paris (CAC 40)
    ".AS": "^AEX",      # Amsterdam
    ".MI": "FTSEMIB.MI",  # Milan
    ".HK": "^HSI",      # Hong Kong
    ".T":  "^N225",     # Tokyo
}
_DEFAULT_INDEX = "^GSPC"


def get_index_for_ticker(ticker: str) -> str:
    """Map a ticker to its home-market index by suffix; falls back to ^GSPC."""
    upper = ticker.upper()
    # Iterate suffixes longest-first so ".DE" doesn't shadow shorter matches.
    for suffix in sorted(_INDEX_BY_SUFFIX, key=len, reverse=True):
        if upper.endswith(suffix):
            return _INDEX_BY_SUFFIX[suffix]
    log.info("no suffix-mapped index for %s; defaulting to %s", ticker, _DEFAULT_INDEX)
    return _DEFAULT_INDEX


# ---------------------------------------------------------------------------
# Tier-3 helpers: fundamentals, insider activity, options-implied move, FX
# ---------------------------------------------------------------------------


def _pct(v: Any) -> float | None:
    """Convert a yfinance decimal (e.g. 0.21) to a percentage (21.0)."""
    f = _f(v)
    return None if f is None else f * 100.0


def get_fundamentals(ticker: str) -> Fundamentals | None:
    info = _get_ticker_info(ticker) or {}
    market_cap = _f(info.get("marketCap"))
    free_cash = _f(info.get("freeCashflow"))
    fcf_yield = (
        free_cash / market_cap * 100.0
        if free_cash is not None and market_cap and market_cap > 0
        else None
    )
    fields = (
        _f(info.get("trailingPE")),
        _f(info.get("forwardPE")),
        _f(info.get("pegRatio")),
        _f(info.get("priceToBook")),
        _f(info.get("enterpriseToEbitda")),
        _pct(info.get("dividendYield")),
        market_cap,
        _f(info.get("debtToEquity")),
        _pct(info.get("profitMargins")),
        _pct(info.get("returnOnEquity")),
        fcf_yield,
    )
    if all(v is None for v in fields):
        return None
    return Fundamentals(
        trailing_pe=fields[0],
        forward_pe=fields[1],
        peg_ratio=fields[2],
        price_to_book=fields[3],
        ev_to_ebitda=fields[4],
        dividend_yield_pct=fields[5],
        market_cap=fields[6],
        debt_to_equity=fields[7],
        profit_margin_pct=fields[8],
        roe_pct=fields[9],
        fcf_yield_pct=fields[10],
    )


def _insider_dollar_value(row: dict[str, Any] | pd.Series) -> float:
    """Coerce yfinance's `Value` column to a positive dollar number."""
    val = row.get("Value") if isinstance(row, pd.Series) else row.get("Value")
    f = _f(val)
    return abs(f) if f is not None else 0.0


def get_insider_activity(ticker: str) -> InsiderActivity | None:
    if ticker in _INSIDER_CACHE:
        return _INSIDER_CACHE[ticker]
    activity: InsiderActivity | None = None
    try:
        df = yf.Ticker(ticker).insider_transactions
        if df is not None and not df.empty:
            cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=90)
            # `Start Date` column is mostly tz-naive in yfinance; normalize.
            dates = pd.to_datetime(df.get("Start Date"), errors="coerce", utc=True)
            mask = dates.notna() & (dates >= cutoff)
            recent = df.loc[mask]
            if not recent.empty:
                buys_dollars = 0.0
                sells_dollars = 0.0
                buys = sells = 0
                shares_net = 0.0
                for _, row in recent.iterrows():
                    txn = str(row.get("Transaction") or "").lower()
                    val = _insider_dollar_value(row)
                    shares = _f(row.get("Shares")) or 0.0
                    if "purchase" in txn or txn == "buy":
                        buys_dollars += val
                        buys += 1
                        shares_net += shares
                    elif "sale" in txn or txn == "sell":
                        sells_dollars += val
                        sells += 1
                        shares_net -= shares
                net_dollars = buys_dollars - sells_dollars
                shares_outstanding = _f((_get_ticker_info(ticker) or {}).get("sharesOutstanding"))
                net_share_pct = (
                    shares_net / shares_outstanding * 100.0
                    if shares_outstanding and shares_outstanding > 0
                    else None
                )
                if buys or sells:
                    activity = InsiderActivity(
                        net_dollars_90d=round(net_dollars, 2),
                        buy_count_90d=buys,
                        sell_count_90d=sells,
                        net_share_pct=(
                            round(net_share_pct, 4) if net_share_pct is not None else None
                        ),
                    )
    except Exception as e:
        log.warning("insider_transactions lookup failed for %s: %s", ticker, e)
    _INSIDER_CACHE[ticker] = activity
    return activity


def _option_mid(row: pd.Series) -> float | None:
    bid = _f(row.get("bid"))
    ask = _f(row.get("ask"))
    if bid is not None and ask is not None and bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    return _f(row.get("lastPrice"))


def get_earnings_implied_move(
    ticker: str,
    current_price: float,
    next_earnings_date: date | datetime | None,
) -> EarningsImpliedMove | None:
    """ATM-straddle-implied move % for the option expiry covering the next print.

    Skip silently when the ticker has no listed options or earnings data is missing.
    """
    if next_earnings_date is None or current_price is None or current_price <= 0:
        return None
    target = next_earnings_date.date() if isinstance(next_earnings_date, datetime) else next_earnings_date
    try:
        t = yf.Ticker(ticker)
        expirations = t.options or ()
        if not expirations:
            return None
        # Pick the earliest expiry on/after the earnings date.
        chosen: date | None = None
        for exp_str in expirations:
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if exp_date >= target:
                chosen = exp_date
                break
        if chosen is None:
            return None
        chain = t.option_chain(chosen.isoformat())
        calls = chain.calls
        puts = chain.puts
        if calls is None or puts is None or calls.empty or puts.empty:
            return None
        atm_call = calls.iloc[(calls["strike"] - current_price).abs().argsort()].iloc[0]
        atm_put = puts.iloc[(puts["strike"] - current_price).abs().argsort()].iloc[0]
        call_mid = _option_mid(atm_call)
        put_mid = _option_mid(atm_put)
        if call_mid is None or put_mid is None:
            return None
        implied_move_pct = (call_mid + put_mid) / current_price * 100.0
        return EarningsImpliedMove(
            implied_move_pct=round(implied_move_pct, 2),
            expiration_date=chosen,
            atm_call_iv=_pct(atm_call.get("impliedVolatility")),
            atm_put_iv=_pct(atm_put.get("impliedVolatility")),
        )
    except Exception as e:
        log.warning("option_chain lookup failed for %s: %s", ticker, e)
        return None


def get_fx_rates(currencies: set[str], home: str = "USD") -> dict[str, float | None]:
    """Last-close FX rates for each non-home currency. Returns `{<CUR>_<HOME>: rate}`."""
    out: dict[str, float | None] = {}
    home_upper = home.upper()
    for cur in {(c or "").upper() for c in currencies}:
        if not cur or cur == home_upper:
            continue
        pair = f"{cur}{home_upper}=X"
        df = get_price_history(pair, period="5d")
        if df is None or df.empty or "Close" not in df.columns:
            out[f"{cur}_{home_upper}"] = None
            continue
        last = _f(df["Close"].astype(float).iloc[-1])
        out[f"{cur}_{home_upper}"] = round(last, 6) if last is not None else None
    return out
