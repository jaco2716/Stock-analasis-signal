"""Discord webhook payload + transport tests using `responses` to mock POSTs."""

from uuid import UUID, uuid4

import pytest
import responses

from lib import discord
from lib.models import Indicators, Profile, Signal


def _profile(webhook: str | None) -> Profile:
    return Profile(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Alice",
        slug="alice",
        discord_webhook_url=webhook,
        is_active=True,
    )


def _indicators() -> Indicators:
    return Indicators(
        last_close=123.45,
        rsi_14=42.7,
        sma_20=120.0,
        sma_50=118.0,
        sma_200=110.0,
        macd=0.5,
        macd_signal=0.4,
        pct_change_30d=2.5,
    )


def _signal(stype: str = "BUY") -> Signal:
    return Signal(
        ticker="NOVO-B.CO",
        signal_type=stype,  # type: ignore[arg-type]
        reasoning="RSI rebounding from oversold; MACD crossed above signal; P&L +12.3%.",
        confidence=0.72,
        profile_id=UUID("11111111-1111-1111-1111-111111111111"),
        run_id=uuid4(),
    )


def _owned_ctx(pnl_pct: float = 12.3, currency: str = "DKK") -> discord.HoldingContext:
    return discord.HoldingContext(
        quantity=50.0,
        cost_basis=37500.0,
        current_value=42125.0,
        pnl_pct=pnl_pct,
        currency=currency,
        is_watchlist=False,
    )


def _watch_ctx(currency: str = "DKK") -> discord.HoldingContext:
    return discord.HoldingContext(
        quantity=None,
        cost_basis=None,
        current_value=None,
        pnl_pct=None,
        currency=currency,
        is_watchlist=True,
    )


@responses.activate
def test_post_signal_uses_profile_webhook_no_prefix() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    responses.add(responses.POST, "https://discord.test/webhooks/profile", status=204)

    discord.post_signal(_signal("BUY"), profile, _indicators(), _owned_ctx())

    assert len(responses.calls) == 1
    body = responses.calls[0].request.body
    payload = body.decode() if isinstance(body, bytes) else body
    assert "[Alice]" not in payload
    assert "BUY NOVO-B.CO" in payload


@responses.activate
def test_post_signal_falls_back_with_prefix() -> None:
    profile = _profile(None)
    responses.add(responses.POST, "https://discord.test/webhooks/default", status=204)

    discord.post_signal(_signal("SELL"), profile, _indicators(), _owned_ctx())

    assert len(responses.calls) == 1
    body = responses.calls[0].request.body
    payload = body.decode() if isinstance(body, bytes) else body
    assert "[Alice] SELL NOVO-B.CO" in payload


def test_build_payload_owned_fields() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    payload = discord.build_payload(
        _signal("BUY"), profile, _indicators(), _owned_ctx(12.3), using_fallback=False
    )
    fields = {f["name"]: f["value"] for f in payload["embeds"][0]["fields"]}
    assert fields["Price (DKK)"] == "123.45"
    assert fields["RSI14"] == "42.7"
    assert fields["Qty"] == "50"
    assert fields["Cost (DKK)"] == "37.500"
    assert fields["Now (DKK)"] == "42.125 (+12.3%)"
    assert fields["Confidence"] == "72%"


def test_build_payload_negative_pnl_sign() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    payload = discord.build_payload(
        _signal("SELL"),
        profile,
        _indicators(),
        discord.HoldingContext(
            quantity=10.0,
            cost_basis=10000.0,
            current_value=8400.0,
            pnl_pct=-16.0,
            currency="DKK",
            is_watchlist=False,
        ),
        using_fallback=False,
    )
    fields = {f["name"]: f["value"] for f in payload["embeds"][0]["fields"]}
    assert fields["Now (DKK)"] == "8.400 (-16.0%)"


def test_build_payload_watchlist_collapses_to_one_field() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    payload = discord.build_payload(
        _signal("HOLD"), profile, _indicators(), _watch_ctx(), using_fallback=False
    )
    field_names = [f["name"] for f in payload["embeds"][0]["fields"]]
    assert "Position" in field_names
    assert "Qty" not in field_names
    assert "Cost (DKK)" not in field_names
    assert "Now (DKK)" not in field_names
    fields = {f["name"]: f["value"] for f in payload["embeds"][0]["fields"]}
    assert fields["Position"] == "Watchlist"


def test_build_payload_colors_and_fallback_prefix() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    buy = discord.build_payload(
        _signal("BUY"), profile, _indicators(), _owned_ctx(), using_fallback=False
    )
    sell = discord.build_payload(
        _signal("SELL"), profile, _indicators(), _watch_ctx(), using_fallback=False
    )
    hold = discord.build_payload(
        _signal("HOLD"), profile, _indicators(), _owned_ctx(), using_fallback=True
    )
    assert buy["embeds"][0]["color"] == 0x16A34A
    assert sell["embeds"][0]["color"] == 0xDC2626
    assert hold["embeds"][0]["color"] == 0x6B7280
    assert hold["embeds"][0]["title"].startswith("[Alice] ")


def test_truncate_reasoning_to_1024() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    long_signal = Signal(
        ticker="X",
        signal_type="HOLD",
        reasoning="x" * 2000,
        confidence=0.5,
        profile_id=profile.id,
        run_id=uuid4(),
    )
    payload = discord.build_payload(
        long_signal, profile, _indicators(), _watch_ctx(), using_fallback=False
    )
    reasoning_field = next(f for f in payload["embeds"][0]["fields"] if f["name"] == "Reasoning")
    assert len(reasoning_field["value"]) <= 1024


@responses.activate
def test_post_signal_dry_run_does_not_post() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    discord.post_signal(_signal(), profile, _indicators(), _owned_ctx(), dry_run=True)
    assert len(responses.calls) == 0


@responses.activate
def test_post_signal_retries_once_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    responses.add(
        responses.POST,
        "https://discord.test/webhooks/profile",
        status=429,
        headers={"Retry-After": "0"},
    )
    responses.add(responses.POST, "https://discord.test/webhooks/profile", status=204)

    sleeps: list[float] = []
    monkeypatch.setattr(discord.time, "sleep", lambda s: sleeps.append(s))

    discord.post_signal(_signal(), profile, _indicators(), _owned_ctx())

    assert len(responses.calls) == 2
    assert sleeps == [0.0]


def _hold_item(
    ticker: str = "NOVO-B.CO",
    is_watchlist: bool = False,
    pnl_pct: float | None = 3.5,
    rsi: float | None = 52.3,
    reasoning: str = "Mixed indicators; no catalyst within 14d.",
) -> discord.HoldSummaryItem:
    return discord.HoldSummaryItem(
        ticker=ticker,
        current_price=487.20,
        currency="DKK",
        rsi_14=rsi,
        confidence=0.65,
        reasoning=reasoning,
        is_watchlist=is_watchlist,
        pnl_pct=pnl_pct,
    )


def test_build_hold_summary_payload_renders_each_item() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    items = [
        _hold_item("NOVO-B.CO", reasoning="Mixed indicators."),
        _hold_item("DSV.CO", pnl_pct=-2.1, reasoning="Sideways awaiting earnings."),
        _hold_item("TSLA", is_watchlist=True, pnl_pct=None, reasoning="No entry trigger."),
    ]
    payload = discord.build_hold_summary_payload(
        items=items, profile=profile, run_id=uuid4(), using_fallback=False
    )
    embed = payload["embeds"][0]
    assert embed["title"] == "📊 HOLD Summary (3)"
    assert embed["color"] == 0x6B7280
    desc = embed["description"]
    assert "**NOVO-B.CO**" in desc
    assert "+3.5%" in desc
    assert "-2.1%" in desc
    # Watchlist line shows the [W] tag but no P&L segment in its header.
    tsla_header = desc.split("**TSLA**")[1].split("\n", 1)[0]
    assert "[W]" in tsla_header
    assert "%" in tsla_header  # confidence %
    assert "+" not in tsla_header and "-" not in tsla_header  # no P&L sign


def test_build_hold_summary_payload_uses_fallback_prefix() -> None:
    profile = _profile(None)
    payload = discord.build_hold_summary_payload(
        items=[_hold_item()], profile=profile, run_id=None, using_fallback=True
    )
    assert payload["embeds"][0]["title"].startswith("[Alice] 📊 HOLD Summary")


def test_build_hold_summary_payload_truncates_long_descriptions() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    items = [_hold_item(f"TICK{i}", reasoning="x" * 500) for i in range(60)]
    payload = discord.build_hold_summary_payload(
        items=items, profile=profile, run_id=uuid4(), using_fallback=False
    )
    assert len(payload["embeds"][0]["description"]) <= 4000


@responses.activate
def test_post_hold_summary_uses_profile_webhook() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    responses.add(responses.POST, "https://discord.test/webhooks/profile", status=204)

    discord.post_hold_summary([_hold_item()], profile, uuid4())

    assert len(responses.calls) == 1
    body = responses.calls[0].request.body
    payload = body.decode() if isinstance(body, bytes) else body
    assert "HOLD Summary" in payload
    assert "[Alice]" not in payload


@responses.activate
def test_post_hold_summary_falls_back_with_prefix() -> None:
    profile = _profile(None)
    responses.add(responses.POST, "https://discord.test/webhooks/default", status=204)

    discord.post_hold_summary([_hold_item()], profile, uuid4())

    assert len(responses.calls) == 1
    body = responses.calls[0].request.body
    payload = body.decode() if isinstance(body, bytes) else body
    assert "[Alice]" in payload
    assert "HOLD Summary" in payload


@responses.activate
def test_post_hold_summary_skips_when_no_items() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    discord.post_hold_summary([], profile, uuid4())
    assert len(responses.calls) == 0


@responses.activate
def test_post_hold_summary_dry_run_does_not_post() -> None:
    profile = _profile("https://discord.test/webhooks/profile")
    discord.post_hold_summary([_hold_item()], profile, uuid4(), dry_run=True)
    assert len(responses.calls) == 0
