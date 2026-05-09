"""Indicator tests against a deterministic synthetic OHLCV series.

The fixture novo_prices.csv was generated with seed=42 from a sine-wave (amplitude 4,
period ~12 trading days) plus uniform noise in [-0.5, +0.5] on Close, with Open derived
from Close +/- a small offset and High/Low padded outwards. 200 weekday rows starting
2024-01-03. Computed expected values (Wilder RSI, simple SMAs) are baked in below.
"""

from pathlib import Path

import pandas as pd
import pytest

from lib.technicals import compute_indicators


def _load(fixtures_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(fixtures_dir / "novo_prices.csv", parse_dates=["Date"])
    return df.set_index("Date")


def test_compute_indicators_known_values(fixtures_dir: Path) -> None:
    df = _load(fixtures_dir)
    ind = compute_indicators(df)

    assert ind.last_close == pytest.approx(97.0571, abs=1e-3)
    assert ind.rsi_14 is not None
    assert ind.rsi_14 == pytest.approx(23.86, abs=0.5)
    assert ind.sma_20 == pytest.approx(99.83, abs=0.1)
    assert ind.sma_50 == pytest.approx(101.56, abs=0.1)
    assert ind.sma_200 == pytest.approx(100.39, abs=0.1)
    assert ind.macd is not None and ind.macd_signal is not None
    assert ind.pct_change_30d is not None


def test_compute_indicators_rsi_in_band(fixtures_dir: Path) -> None:
    df = _load(fixtures_dir)
    ind = compute_indicators(df)
    rsi = ind.rsi_14
    assert rsi is not None
    assert 0.0 <= rsi <= 100.0


def test_compute_indicators_short_frame_no_sma200() -> None:
    # 50 rows: SMA200 must be None, SMA50 should be defined.
    closes = [100.0 + (i % 5) for i in range(50)]
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 0.5 for c in closes],
            "Low": [c - 0.5 for c in closes],
            "Close": closes,
            "Volume": [1_000_000] * 50,
        }
    )
    ind = compute_indicators(df)
    assert ind.sma_200 is None
    assert ind.sma_50 is not None


def test_compute_indicators_rejects_empty() -> None:
    with pytest.raises(ValueError):
        compute_indicators(pd.DataFrame())
