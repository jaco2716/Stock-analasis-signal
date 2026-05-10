"""Queue helpers in run_analysis.py: write on HOLD, flush at finish-run."""

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import run_analysis
from lib import discord
from lib.models import Profile


def _profile(webhook: str | None = "https://discord.test/webhooks/profile") -> Profile:
    return Profile(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        name="Alice",
        slug="alice",
        discord_webhook_url=webhook,
        is_active=True,
    )


def _item(ticker: str = "NOVO-B.CO") -> discord.HoldSummaryItem:
    return discord.HoldSummaryItem(
        ticker=ticker,
        current_price=487.20,
        currency="DKK",
        rsi_14=52.0,
        confidence=0.6,
        reasoning="Mixed indicators.",
        is_watchlist=False,
        pnl_pct=3.5,
    )


def test_enqueue_appends_per_profile_bucket(tmp_path: Path) -> None:
    queue_path = tmp_path / "holds.json"
    run_id = uuid4()
    profile = _profile()

    run_analysis._enqueue_hold(queue_path, run_id, profile, _item("A"))
    run_analysis._enqueue_hold(queue_path, run_id, profile, _item("B"))

    queue = json.loads(queue_path.read_text())
    assert queue["run_id"] == str(run_id)
    bucket = queue["profiles"][str(profile.id)]
    assert bucket["profile"]["slug"] == "alice"
    assert [it["ticker"] for it in bucket["items"]] == ["A", "B"]


def test_enqueue_with_different_run_resets_queue(tmp_path: Path) -> None:
    queue_path = tmp_path / "holds.json"
    profile = _profile()

    run_analysis._enqueue_hold(queue_path, uuid4(), profile, _item("OLD"))
    new_run = uuid4()
    run_analysis._enqueue_hold(queue_path, new_run, profile, _item("NEW"))

    queue = json.loads(queue_path.read_text())
    assert queue["run_id"] == str(new_run)
    tickers = [it["ticker"] for it in queue["profiles"][str(profile.id)]["items"]]
    assert tickers == ["NEW"]


def test_clear_holds_queue_removes_file(tmp_path: Path) -> None:
    queue_path = tmp_path / "holds.json"
    queue_path.write_text("{}")
    run_analysis._clear_holds_queue(queue_path)
    assert not queue_path.exists()
    # idempotent
    run_analysis._clear_holds_queue(queue_path)


def test_flush_calls_post_hold_summary_per_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_path = tmp_path / "holds.json"
    run_id = uuid4()
    profile = _profile()
    run_analysis._enqueue_hold(queue_path, run_id, profile, _item("A"))
    run_analysis._enqueue_hold(queue_path, run_id, profile, _item("B"))

    calls: list[tuple[list, Profile, UUID, bool]] = []

    def fake_post(items, prof, rid, dry_run=False):  # type: ignore[no-untyped-def]
        calls.append((list(items), prof, rid, dry_run))

    monkeypatch.setattr(discord, "post_hold_summary", fake_post)

    run_analysis._flush_holds_queue(queue_path, run_id, dry_run=False)

    assert len(calls) == 1
    items, prof, rid, dry = calls[0]
    assert [i.ticker for i in items] == ["A", "B"]
    assert prof.id == profile.id
    assert rid == run_id
    assert dry is False
    assert not queue_path.exists()


def test_flush_skips_when_run_id_does_not_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_path = tmp_path / "holds.json"
    run_analysis._enqueue_hold(queue_path, uuid4(), _profile(), _item("A"))

    calls: list = []
    monkeypatch.setattr(
        discord,
        "post_hold_summary",
        lambda *a, **k: calls.append(a),  # type: ignore[no-untyped-def]
    )

    run_analysis._flush_holds_queue(queue_path, uuid4(), dry_run=False)

    assert calls == []
    # queue is left intact for the run that owns it
    assert queue_path.exists()


def test_flush_dry_run_keeps_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_path = tmp_path / "holds.json"
    run_id = uuid4()
    run_analysis._enqueue_hold(queue_path, run_id, _profile(), _item("A"))

    monkeypatch.setattr(discord, "post_hold_summary", lambda *a, **k: None)

    run_analysis._flush_holds_queue(queue_path, run_id, dry_run=True)
    assert queue_path.exists()


def test_flush_no_queue_is_noop(tmp_path: Path) -> None:
    run_analysis._flush_holds_queue(tmp_path / "missing.json", uuid4(), dry_run=False)
