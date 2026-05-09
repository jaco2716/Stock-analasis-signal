"""Pure indicator computation; no I/O, fully unit-testable."""

import pandas as pd

from .models import Indicators


def _wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # alpha=1/period reproduces Wilder's smoothing; matches pandas-ta and most charting libs.
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig


def _last_or_none(s: pd.Series) -> float | None:
    if s is None or s.empty:
        return None
    v = s.iloc[-1]
    if pd.isna(v):
        return None
    return float(v)


def compute_indicators(df: pd.DataFrame) -> Indicators:
    if df is None or df.empty or "Close" not in df.columns:
        raise ValueError("compute_indicators requires a non-empty frame with a 'Close' column")
    close = df["Close"].astype(float)

    rsi = _wilder_rsi(close, 14)
    sma_20 = close.rolling(20).mean()
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()
    macd, macd_sig = _macd(close)

    pct_30d: float | None = None
    if len(close) >= 31:
        prev = close.iloc[-31]
        last = close.iloc[-1]
        if prev:
            pct_30d = float((last - prev) / prev * 100.0)

    return Indicators(
        last_close=float(close.iloc[-1]),
        rsi_14=_last_or_none(rsi),
        sma_20=_last_or_none(sma_20),
        sma_50=_last_or_none(sma_50),
        sma_200=_last_or_none(sma_200),
        macd=_last_or_none(macd),
        macd_signal=_last_or_none(macd_sig),
        pct_change_30d=pct_30d,
    )
