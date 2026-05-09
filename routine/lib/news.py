"""Fetch a small news digest for a ticker via Anthropic's web_search server tool."""

import logging
from typing import cast

from anthropic import Anthropic

from .analyzer import MODEL
from .config import get_settings
from .models import NewsDigest, Sentiment

log = logging.getLogger(__name__)

_VALID_SENTIMENTS: set[str] = {"BULLISH", "BEARISH", "NEUTRAL", "MIXED"}

_DIGEST_TOOL = {
    "name": "emit_digest",
    "description": "Emit a structured news digest for the ticker under review.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headlines": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
                "maxItems": 5,
            },
            "summary": {"type": "string", "maxLength": 240},
            "sentiment": {
                "type": "string",
                "enum": ["BULLISH", "BEARISH", "NEUTRAL", "MIXED"],
            },
        },
        "required": ["headlines", "summary", "sentiment"],
    },
}

_SYSTEM = (
    "You produce concise news digests for equity analysis. Use the web_search tool to "
    "find recent items, then call the emit_digest tool exactly once with a structured "
    "result. Headlines must be short and factual; summary is one sentence."
)


def _extract_digest_input(message) -> dict | None:
    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", "") == "emit_digest":
            return dict(block.input)
    return None


def fetch_news_digest(ticker: str, name: str) -> NewsDigest:
    client = Anthropic(api_key=get_settings().anthropic_api_key)
    prompt = (
        f"Find 3-5 most relevant news items for {ticker} ({name}) from the last 14 days. "
        "Return concise headlines + a one-sentence sentiment summary."
    )
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=_SYSTEM,
            tools=[
                {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
                _DIGEST_TOOL,
            ],
            tool_choice={"type": "tool", "name": "emit_digest"},
            messages=[{"role": "user", "content": prompt}],
        )
        payload = _extract_digest_input(message)
        if payload is None:
            raise ValueError("model did not invoke emit_digest")
        headlines = [str(h) for h in payload.get("headlines", [])][:5]
        summary = str(payload.get("summary", "")).strip()
        sentiment_raw = str(payload.get("sentiment", "NEUTRAL")).upper().strip()
        sentiment: Sentiment = cast(
            Sentiment, sentiment_raw if sentiment_raw in _VALID_SENTIMENTS else "NEUTRAL"
        )
        return NewsDigest(headlines=headlines, summary=summary, sentiment=sentiment)
    except Exception:
        log.exception("news digest failed for %s", ticker)
        return NewsDigest(headlines=[], summary="No news available.", sentiment="NEUTRAL")
