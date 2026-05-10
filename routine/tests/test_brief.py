"""Brief assembly: verifies the new Tier-1 fields populate and degrade gracefully."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pandas as pd
import pytest

from lib import brief
from lib.models import (
    AnalystConsensus,
    EarningsImpliedMove,
    Fundamentals,
    Holding,
    Indicators,
    InsiderActivity,
    RealtimeQuote,
    SignalRecord,
)


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


# --------------------------- Tier-2 fields --------------------------------


def test_realtime_fields_populate_when_provided() -> None:
    rt = RealtimeQuote(
        intraday_price=87.5,
        intraday_change_pct=-1.2,
        pre_market_price=88.0,
        pre_market_change_pct=0.5,
        market_state="REGULAR",
    )
    section = brief.build_holding_section(_holding(), _prices(), _indicators(), realtime=rt)
    assert section["intraday_price"] == 87.5
    assert section["intraday_change_pct"] == -1.2
    assert section["pre_market_price"] == 88.0
    assert section["market_state"] == "REGULAR"


def test_realtime_fields_default_to_null() -> None:
    section = brief.build_holding_section(_holding(), _prices(), _indicators())
    for key in (
        "intraday_price",
        "intraday_change_pct",
        "pre_market_price",
        "pre_market_change_pct",
        "market_state",
    ):
        assert section[key] is None


def test_analyst_target_distance_pct_derived() -> None:
    ac = AnalystConsensus(
        target_mean=100.0,
        target_high=130.0,
        target_low=80.0,
        recommendation_key="buy",
        analyst_count=20,
    )
    section = brief.build_holding_section(_holding(), _prices(), _indicators(), analyst=ac)
    # current_price comes from prices fixture (50 + 259 % 11 = 50 + 6 = 56)
    expected_distance = round((100.0 / section["current_price"] - 1) * 100, 2)
    assert section["analyst_target_distance_pct"] == expected_distance
    assert section["analyst_recommendation_key"] == "buy"
    assert section["analyst_count"] == 20


def test_analyst_fields_default_to_null() -> None:
    section = brief.build_holding_section(_holding(), _prices(), _indicators())
    for key in (
        "analyst_target_mean",
        "analyst_target_distance_pct",
        "analyst_target_high",
        "analyst_target_low",
        "analyst_recommendation_key",
        "analyst_count",
    ):
        assert section[key] is None


def test_relative_strength_serializes_top_level() -> None:
    rs = {
        "baseline_index": "^OMXC25",
        "baseline_pct_change_30d": -1.4,
        "relative_strength_30d_pct": 4.7,
    }
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), relative_strength=rs
    )
    assert section["baseline_index"] == "^OMXC25"
    assert section["baseline_pct_change_30d"] == -1.4
    assert section["relative_strength_30d_pct"] == 4.7
    # Sector keys are absent when no mapping was supplied.
    assert "sector_benchmark" not in section


def test_sector_relative_strength_fields_emitted() -> None:
    rs = {
        "baseline_index": "^GSPC",
        "baseline_pct_change_30d": 14.2,
        "relative_strength_30d_pct": 12.0,
        "sector_benchmark": "SMH",
        "sector_pct_change_30d": 22.0,
        "sector_relative_strength_30d_pct": 4.2,
    }
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), relative_strength=rs
    )
    assert section["sector_benchmark"] == "SMH"
    assert section["sector_pct_change_30d"] == 22.0
    assert section["sector_relative_strength_30d_pct"] == 4.2


def test_next_earnings_date_and_days_until() -> None:
    today = datetime.now(timezone.utc).date()
    next_date = today + timedelta(days=21)
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), next_earnings_date=next_date
    )
    assert section["next_earnings_date"] == next_date.isoformat()
    assert section["days_until_earnings"] == 21


def test_next_earnings_date_in_past_yields_null_days_until() -> None:
    past = datetime.now(timezone.utc) - timedelta(days=3)
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), next_earnings_date=past
    )
    assert section["days_until_earnings"] is None


# --------------------------- Tier-3 fields --------------------------------


def _funda() -> Fundamentals:
    return Fundamentals(
        trailing_pe=18.0,
        forward_pe=16.0,
        peg_ratio=0.9,
        price_to_book=4.5,
        ev_to_ebitda=12.0,
        dividend_yield_pct=2.0,
        market_cap=1e9,
        debt_to_equity=70.0,
        profit_margin_pct=18.0,
        roe_pct=22.0,
        fcf_yield_pct=5.5,
    )


def test_fundamentals_block_populated() -> None:
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), fundamentals=_funda()
    )
    f = section["fundamentals"]
    assert f["trailing_pe"] == 18.0
    assert f["fcf_yield_pct"] == 5.5
    assert f["dividend_yield_pct"] == 2.0


def test_fundamentals_block_defaults_to_none() -> None:
    section = brief.build_holding_section(_holding(), _prices(), _indicators())
    assert section["fundamentals"] is None


def test_insider_block_defaults_to_none() -> None:
    section = brief.build_holding_section(_holding(), _prices(), _indicators())
    assert section["insider"] is None


def test_implied_move_block_defaults_to_none() -> None:
    section = brief.build_holding_section(_holding(), _prices(), _indicators())
    assert section["earnings_implied_move"] is None


def test_blocks_collapse_when_all_subfields_null() -> None:
    empty_funda = Fundamentals(
        trailing_pe=None,
        forward_pe=None,
        peg_ratio=None,
        price_to_book=None,
        ev_to_ebitda=None,
        dividend_yield_pct=None,
        market_cap=None,
        debt_to_equity=None,
        profit_margin_pct=None,
        roe_pct=None,
        fcf_yield_pct=None,
    )
    empty_insider = InsiderActivity(
        net_dollars_90d=None, buy_count_90d=None, sell_count_90d=None, net_share_pct=None
    )
    section = brief.build_holding_section(
        _holding(),
        _prices(),
        _indicators(),
        fundamentals=empty_funda,
        insider=empty_insider,
    )
    assert section["fundamentals"] is None
    assert section["insider"] is None


def test_recent_closes_field_removed() -> None:
    section = brief.build_holding_section(_holding(), _prices(), _indicators())
    assert "recent_closes" not in section


def test_insider_block_populated() -> None:
    insider = InsiderActivity(
        net_dollars_90d=120_000.0, buy_count_90d=2, sell_count_90d=1, net_share_pct=0.12
    )
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), insider=insider
    )
    i = section["insider"]
    assert i["net_dollars_90d"] == 120_000.0
    assert i["buy_count_90d"] == 2
    assert i["sell_count_90d"] == 1


def test_implied_move_block_serialises_date() -> None:
    from datetime import date as _date

    move = EarningsImpliedMove(
        implied_move_pct=4.8,
        expiration_date=_date(2026, 5, 22),
        atm_call_iv=50.0,
        atm_put_iv=52.0,
    )
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), implied_move=move
    )
    m = section["earnings_implied_move"]
    assert m["implied_move_pct"] == 4.8
    assert m["expiration_date"] == "2026-05-22"
    assert m["atm_call_iv"] == 50.0


def test_position_weight_pct_round_trip() -> None:
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), position_weight_pct=12.345
    )
    assert section["position_weight_pct"] == 12.34 or section["position_weight_pct"] == 12.35


def test_signal_history_outcomes_passthrough() -> None:
    now = datetime.now(timezone.utc)
    history = [
        SignalRecord(
            ticker="ABC",
            signal_type="BUY",
            confidence=0.8,
            generated_at=now - timedelta(days=10),
            run_id=uuid4(),
            outcome_t5_pct=2.5,
            outcome_t30_pct=None,
        ),
        SignalRecord(
            ticker="ABC",
            signal_type="HOLD",
            confidence=0.5,
            generated_at=now - timedelta(days=2),
            run_id=uuid4(),
        ),
    ]
    section = brief.build_holding_section(
        _holding(), _prices(), _indicators(), signal_history=history
    )
    assert section["signal_history"][0]["outcome_t5_pct"] == 2.5
    # Newer entry has no outcomes yet, so the keys are absent.
    assert "outcome_t5_pct" not in section["signal_history"][1]


def test_profile_section_carries_totals_and_fx() -> None:
    from lib.models import Profile

    prof = Profile(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Default",
        slug="default",
        discord_webhook_url=None,
        is_active=True,
    )
    totals = {"USD": {"total_cost_basis": 5000.0, "total_current_value": 6000.0, "holding_count": 3}}
    fx = {"DKK_USD": 0.146}
    out = brief.build_profile_section(prof, [], portfolio_totals=totals, fx_rates=fx)
    assert out["portfolio_totals"]["USD"]["holding_count"] == 3
    assert out["fx_rates"]["DKK_USD"] == 0.146
