"""yfinance wrapper with retries and a per-run cache."""

import logging
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)

# Per-run caches; cleared by run_analysis.main before iteration starts.
_CACHE: dict[tuple[str, str], pd.DataFrame] = {}
_EARNINGS_CACHE: dict[str, datetime | None] = {}


def clear_cache() -> None:
    _CACHE.clear()
    _EARNINGS_CACHE.clear()


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


def get_last_earnings_date(ticker: str) -> datetime | None:
    """Most recent past earnings date from yfinance, or None when unavailable.

    yfinance's `earnings_dates` is flaky for non-US tickers and can raise on rate
    limits, so any failure resolves to None rather than aborting the brief.
    """
    if ticker in _EARNINGS_CACHE:
        return _EARNINGS_CACHE[ticker]
    result: datetime | None = None
    try:
        df = yf.Ticker(ticker).earnings_dates
        if df is not None and not df.empty:
            now = pd.Timestamp.now(tz="UTC")
            past = df.index[df.index <= now]
            if len(past) > 0:
                ts = past.max()
                if ts.tzinfo is None:
                    ts = ts.tz_localize("UTC")
                result = ts.to_pydatetime().astimezone(timezone.utc)
    except Exception as e:
        log.warning("earnings_dates lookup failed for %s: %s", ticker, e)
    _EARNINGS_CACHE[ticker] = result
    return result
