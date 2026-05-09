"""yfinance wrapper with retries and a per-run cache."""

import logging

import pandas as pd
import yfinance as yf
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)

# Per-run cache; cleared by run_analysis.main before iteration starts.
_CACHE: dict[tuple[str, str], pd.DataFrame] = {}


def clear_cache() -> None:
    _CACHE.clear()


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
