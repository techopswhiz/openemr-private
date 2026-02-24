# AI-generated: Claude Code (claude.ai/code) — conversation memory store
from langchain_core.messages import BaseMessage

# In-memory session store — keyed by session_id
_sessions: dict[str, list[BaseMessage]] = {}

# Cap history to avoid unbounded growth
MAX_MESSAGES = 50


def get_history(session_id: str) -> list[BaseMessage]:
    return _sessions.get(session_id, [])


def save_history(session_id: str, messages: list[BaseMessage]) -> None:
    _sessions[session_id] = messages[-MAX_MESSAGES:]


def clear_history(session_id: str) -> None:
    _sessions.pop(session_id, None)
# end AI-generated
