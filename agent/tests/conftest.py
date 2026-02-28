# AI-generated: Claude Code (claude.ai/code) — test fixtures
import pytest


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Set minimal env vars for tests."""
    monkeypatch.setenv("XAI_API_KEY", "test-key")
# end AI-generated
