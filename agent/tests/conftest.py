# AI-generated: Claude Code (claude.ai/code) — test fixtures
import os
import pytest


@pytest.fixture(autouse=True)
def demo_mode(monkeypatch):
    """Force demo mode for all tests."""
    monkeypatch.setenv("OPENEMR_CLIENT_ID", "")
    monkeypatch.setenv("XAI_API_KEY", "test-key")
# end AI-generated
