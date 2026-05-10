"""Domain dataclasses mirroring the Supabase schema and run-time DTOs."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

SignalType = Literal["BUY", "SELL", "HOLD"]
HoldingKind = Literal["owned", "watchlist"]
RunStatus = Literal["running", "success", "partial", "failed"]


@dataclass(frozen=True)
class Profile:
    id: UUID
    name: str
    slug: str
    discord_webhook_url: str | None
    is_active: bool


@dataclass(frozen=True)
class Holding:
    id: UUID
    profile_id: UUID
    ticker: str
    name: str
    quantity: float | None
    avg_buy_price: float | None
    currency: str
    kind: HoldingKind


@dataclass(frozen=True)
class Indicators:
    last_close: float
    rsi_14: float | None
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    macd: float | None
    macd_signal: float | None
    pct_change_30d: float | None


@dataclass
class Signal:
    ticker: str
    signal_type: SignalType
    reasoning: str
    confidence: float
    profile_id: UUID | None = None
    run_id: UUID | None = None
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class RunContext:
    run_id: UUID
    started_at: datetime
    dry_run: bool
