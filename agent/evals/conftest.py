# AI-generated: Claude Code (claude.ai/code) — eval fixtures
import os

import httpx
import pytest


AGENT_BASE_URL = os.environ.get("AGENT_BASE_URL", "http://localhost:8080")


@pytest.fixture(scope="session")
def agent_url():
    """Base URL of the running agent. Set AGENT_BASE_URL env var to override."""
    return AGENT_BASE_URL


@pytest.fixture(scope="session")
def agent_healthy(agent_url):
    """Skip all evals if the agent isn't reachable."""
    try:
        r = httpx.get(f"{agent_url}/health", timeout=5)
        r.raise_for_status()
    except (httpx.ConnectError, httpx.HTTPStatusError):
        pytest.skip(f"Agent not reachable at {agent_url}")


def _new_session_id():
    import uuid
    return f"eval-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def session_id():
    """Unique session ID per test to avoid conversation bleed."""
    return _new_session_id()


@pytest.fixture
def chat(agent_url, agent_healthy, session_id):
    """Send a message to the agent and return the full response dict.

    Returns a callable: chat("message") -> {response, tool_calls, verification_warnings}
    """
    async def _chat(message: str) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{agent_url}/chat",
                json={"message": message, "session_id": session_id},
            )
            r.raise_for_status()
            return r.json()
    return _chat
# end AI-generated
