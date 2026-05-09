"""Analyzer tests: mock the Anthropic client; assert forced tool_use is parsed into a Signal."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pandas as pd
import pytest

from lib import analyzer
from lib.models import Holding, Indicators, NewsDigest


def _holding() -> Holding:
    return Holding(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        profile_id=UUID("11111111-1111-1111-1111-111111111111"),
        ticker="NOVO-B.CO",
        name="Novo Nordisk B",
        position_dkk=10000.0,
        kind="owned",
    )


def _prices() -> pd.DataFrame:
    closes = [100.0 + i * 0.1 for i in range(60)]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 0.5 for c in closes],
            "Low": [c - 0.5 for c in closes],
            "Close": closes,
            "Volume": [1_000_000] * 60,
        }
    )


def _indicators() -> Indicators:
    return Indicators(
        last_close=105.9,
        rsi_14=58.2,
        sma_20=104.5,
        sma_50=103.0,
        sma_200=None,
        macd=0.3,
        macd_signal=0.2,
        pct_change_30d=3.1,
    )


def _news() -> NewsDigest:
    return NewsDigest(
        headlines=["Strong Q1 earnings", "Pipeline update positive"],
        summary="Fundamentals improving; sentiment bullish.",
        sentiment="BULLISH",
    )


def _mock_message(signal_type: str = "BUY", confidence: float = 0.78,
                  reasoning: str = "RSI healthy; MACD positive; news bullish.") -> SimpleNamespace:
    tool_block = SimpleNamespace(
        type="tool_use",
        name="emit_signal",
        input={"signal_type": signal_type, "confidence": confidence, "reasoning": reasoning},
    )
    text_block = SimpleNamespace(type="text", text="ignored")
    return SimpleNamespace(content=[text_block, tool_block])


def test_analyze_holding_parses_tool_use_into_signal() -> None:
    client = MagicMock()
    client.messages.create.return_value = _mock_message("BUY", 0.78, "Bullish setup.")

    sig = analyzer.analyze_holding(_holding(), _prices(), _indicators(), _news(), client=client)

    assert sig.ticker == "NOVO-B.CO"
    assert sig.signal_type == "BUY"
    assert sig.confidence == pytest.approx(0.78)
    assert sig.reasoning == "Bullish setup."

    # Confirm the call used forced tool use against the right tool.
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == analyzer.MODEL
    assert kwargs["tool_choice"] == {"type": "tool", "name": "emit_signal"}
    assert any(t.get("name") == "emit_signal" for t in kwargs["tools"])


def test_analyze_holding_clamps_confidence_and_truncates_reasoning() -> None:
    client = MagicMock()
    client.messages.create.return_value = _mock_message("HOLD", 1.5, "x" * 1200)

    sig = analyzer.analyze_holding(_holding(), _prices(), _indicators(), _news(), client=client)

    assert sig.confidence == 1.0
    assert len(sig.reasoning) == 800


def test_analyze_holding_raises_when_no_tool_use() -> None:
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="no tool call here")]
    )
    with pytest.raises(ValueError):
        analyzer.analyze_holding(_holding(), _prices(), _indicators(), _news(), client=client)
