"""yfinance wrapper with retries and a per-run cache."""

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .models import AnalystConsensus, EarningsCalendar, RealtimeQuote

log = logging.getLogger(__name__)

# Per-run caches; cleared by run_analysis.main before iteration starts.
_CACHE: dict[tuple[str, str], pd.DataFrame] = {}
_EARNINGS_CAL_CACHE: dict[str, EarningsCalendar] = {}
_INFO_CACHE: dict[str, dict[str, Any] | None] = {}


def clear_cache() -> None:
    _CACHE.clear()
    _EARNINGS_CAL_CACHE.clear()
    _INFO_CACHE.clear()


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
