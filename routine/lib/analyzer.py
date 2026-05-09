"""The single LLM judgment site: forced tool use produces one Signal per holding."""

import logging
from dataclasses import asdict

import pandas as pd
from anthropic import Anthropic

from .config import get_settings
from .models import Holding, Indicators, NewsDigest, Signal, SignalType

log = logging.getLogger(__name__)

MODEL = "claude-opus-4-7"

_TOOL = {
    "name": "emit_signal",
    "description": "Emit a single trading signal for the holding under analysis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "signal_type": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string", "maxLength": 800},
        },
        "required": ["signal_type", "confidence", "reasoning"],
    },
}

_SYSTEM = (
    "You are a disciplined equity analyst. Given technical indicators, recent price action, "
    "and a news digest, emit exactly one signal via the emit_signal tool. Be conservative: "
    "default to HOLD when evidence is mixed. Confidence reflects strength of evidence, not "
    "magnitude of expected move. Reasoning must cite specific indicators and news points."
)


def _summarize_prices(prices: pd.DataFrame) -> str:
    tail = prices["Close"].astype(float).tail(10).tolist()
    return ", ".join(f"{v:.2f}" for v in tail)


def _build_user_prompt(
    holding: Holding, prices: pd.DataFrame, indicators: Indicators, news: NewsDigest
) -> str:
    pos_line = (
        f"Position: {holding.position_dkk:.0f} DKK"
        if holding.position_dkk is not None
        else "Position: watchlist (no position)"
    )
    ind = asdict(indicators)
    ind_lines = "\n".join(f"  {k}: {v}" for k, v in ind.items())
    headlines = "\n".join(f"  - {h}" for h in news.headlines) or "  (none)"
    return (
        f"Ticker: {holding.ticker} ({holding.name})\n"
        f"Kind: {holding.kind}\n"
        f"{pos_line}\n\n"
        f"Last 10 closes: {_summarize_prices(prices)}\n\n"
        f"Indicators:\n{ind_lines}\n\n"
        f"News sentiment: {news.sentiment}\n"
        f"News summary: {news.summary}\n"
        f"Headlines:\n{headlines}\n\n"
        "Call emit_signal exactly once."
    )


def _extract_tool_input(message) -> dict:
    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", "") == "emit_signal":
            return dict(block.input)
    raise ValueError("analyzer: model did not invoke the emit_signal tool")


def analyze_holding(
    holding: Holding,
    prices: pd.DataFrame,
    indicators: Indicators,
    news: NewsDigest,
    client: Anthropic | None = None,
) -> Signal:
    client = client or Anthropic(api_key=get_settings().anthropic_api_key)
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "emit_signal"},
        messages=[{"role": "user", "content": _build_user_prompt(holding, prices, indicators, news)}],
    )
    payload = _extract_tool_input(message)

    signal_type: SignalType = payload["signal_type"]
    confidence = float(payload["confidence"])
    confidence = max(0.0, min(1.0, confidence))
    reasoning = str(payload["reasoning"])[:800]

    return Signal(
        ticker=holding.ticker,
        signal_type=signal_type,
        reasoning=reasoning,
        confidence=confidence,
    )
