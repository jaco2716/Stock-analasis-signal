"""Test fixtures: ensure routine/ is importable and seed env so Settings instantiates."""

import os
import sys
from pathlib import Path

import pytest

ROUTINE_ROOT = Path(__file__).resolve().parents[1]
if str(ROUTINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ROUTINE_ROOT))


@pytest.fixture(autouse=True)
def _stub_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://stub.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "stub-key")
    monkeypatch.setenv("DEFAULT_DISCORD_WEBHOOK_URL", "https://discord.test/webhooks/default")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    # Force a fresh Settings on each test by clearing the lru_cache.
    from lib.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
