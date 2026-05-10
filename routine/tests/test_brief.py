"""Brief assembly: verifies the new Tier-1 fields populate and degrade gracefully."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pandas as pd
import pytest

from lib import brief
from lib.models import Holding, Indicators, SignalRecord


def _holding(kind: str = "owned") -> Holding:
    return Holding(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        profile_id=UUID("11111111-1111-1111-1111-111111111111"),
        ticker="ABC",
        name="ABC Corp",
        quantity=10.0 if kind == "owned" else None,
        avg_buy_price=50.0 if kind == "owned" else None,
        currency="USD",
        kind=kind,  # type: ignore[arg-type]
    )


def _prices(rows: int = 260, with_ohlcv: bool = True) -> pd.DataFrame:
    closes = [50.0 + (i % 11) for i in range(rows)]
    data = {"Close": closes}
    if with_ohlcv:
        data["Open"] = [c - 0.2 for c in closes]
        data["High"] = [c + 1.0 for c in closes]
        data["Low"] = [c - 1.0 for c in closes]
        data["Volume"] = [1_000_000 + (i % 17) * 10_000 for i in range(rows)]
    idx = pd.bdate_range(end="2026-05-08", periods=rows)
    return pd.DataFrame(data, index=idx)


def _indicators(atr: float | None = 1.5) -> Indicators:
    return Indicators(
        last_close=60.0,
        rsi_14=55.0,
        sma_20=58.0,
        sma_50=57.0,
        sma_200=54.0,
        macd=0.4,
        macd_signal=0.3,
        pct_change_30d=2.5,
        atr_14=atr,
    )


def test_holding_section_includes_new_keys() -> None:
    section = brief.build_holding_section(_holding(), _prices(), _indicators())
    for key in (
        "high_52w",
        "low_52w",
        "pct_below_52w_high",
        "pct_above_52w_low",
        "volume_last",
        "volume_20d_avg",
        "volume_vs_avg_x",
        "last_earnings_date",
        "days_since_earnings",
        "signal_history",
    ):
        assert key in section, f"missing key: {key}"
    assert "atr_pct_of_price" in section["indicators"]
    assert section["signal_history"] == []
    assert section["last_earnings_date"] is None
    assert section["days_since_earnings"] is None


def test_high_low_52w_distance_signs() -> None:
    section = brief.build_holding_section(_holding(), _prices(), _indicators())
    # current_price = last close = 50 + (259 % 11) = 50 + 6 = 56
    assert section["current_price"] == 56.0
    assert section["high_52w"] >= section["current_price"]
    assert section["low_52w"] <= section["current_price"]
    assert section["pct_below_52w_high"] <= 0
    assert section["pct_above_52w_low"] >= 0


def test_atr_pct_of_price_derived() -> None:
    # _atr_pct_of_price uses indicators.last_close (the indicator-world close), not the
    # brief's current_price — they're the same in production because both originate
    # from the same DataFrame.
    indicators = _indicators(atr=2.0)
    section = brief.build_holding_section(_holding(), _prices(), indicators)
    expected = 2.0 / indicators.last_close * 100.0
    assert section["indicators"]["atr_pct_of_price"] == pytest.approx(expected, abs=1e-3)


def test_atr_pct_none_when_atr_missing() -> None:
    section = brief.build_holding_section(_holding(), _prices(), _indicators(atr=None))
    assert section["indicators"]["atr_pct_of_price"] is None


def test_volume_context_short_frame() -> None:
    short = _prices(rows=15)
    section = brief.build_holding_section(_holding(), short, _indicators())
    # 15 < _LOOKBACK_52W minimum (20) -> 52w fields all null
    assert section["high_52w"] is None
    assert section["low_52w"] is None
    # volume context still computes on whatever's there
    assert section["volume_last"] is not None


def test_no_high_low_columns_handles_gracefully() -> None:
    no_ohlc = _prices(with_ohlcv=False)
    section = brief.build_holding_section(_holding(), no_ohlc, _indicators())
    assert section["high_52w"] is None
    assert section["volume_last"] is None
    assert section["volume_20d_avg"] is None


def test_earnings_date_serializes_iso_and_days() -> None:
    earnings = datetime.now(timezone.utc) - timedelta(days=12)
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), last_earnings_date=earnings
    )
    assert section["last_earnings_date"] == earnings.date().isoformat()
    assert section["days_since_earnings"] == 12


def test_signal_history_serialization() -> None:
    now = datetime.now(timezone.utc)
    history = [
        SignalRecord(
            ticker="ABC",
            signal_type="HOLD",
            confidence=0.6,
            generated_at=now - timedelta(days=1),
            run_id=uuid4(),
        ),
        SignalRecord(
            ticker="ABC",
            signal_type="BUY",
            confidence=0.8,
            generated_at=now - timedelta(days=7),
            run_id=uuid4(),
        ),
    ]
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), signal_history=history
    )
    assert len(section["signal_history"]) == 2
    assert section["signal_history"][0]["signal_type"] == "HOLD"
    assert section["signal_history"][0]["confidence"] == 0.6
    assert "generated_at" in section["signal_history"][0]
