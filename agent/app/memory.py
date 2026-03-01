# AI-generated: Claude Code (claude.ai/code) — persistent conversation memory (SQLite)
import json
import sqlite3
import time
from pathlib import Path

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.config import settings

MAX_MESSAGES = 50
SESSION_TTL_SECONDS = 86400  # 24 hours


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.memory_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            messages TEXT NOT NULL,
            updated_at REAL NOT NULL
        )"""
    )
    conn.commit()
    return conn


def _serialize_message(msg: BaseMessage) -> dict:
    """Convert a LangChain message to a JSON-safe dict."""
    data: dict = {"type": type(msg).__name__, "content": msg.content}
    if isinstance(msg, AIMessage) and msg.tool_calls:
        data["tool_calls"] = msg.tool_calls
    if isinstance(msg, ToolMessage):
        data["tool_call_id"] = msg.tool_call_id
        data["name"] = msg.name
        if hasattr(msg, "artifact") and msg.artifact is not None:
            data["artifact"] = msg.artifact
    if hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
        data["additional_kwargs"] = msg.additional_kwargs
    return data


def _deserialize_message(data: dict) -> BaseMessage:
    """Reconstruct a LangChain message from a stored dict."""
    msg_type = data["type"]
    content = data["content"]

    if msg_type == "HumanMessage":
        return HumanMessage(content=content)
    elif msg_type == "SystemMessage":
        return SystemMessage(content=content)
    elif msg_type == "AIMessage":
        kwargs: dict = {}
        if "tool_calls" in data:
            kwargs["tool_calls"] = data["tool_calls"]
        if "additional_kwargs" in data:
            kwargs["additional_kwargs"] = data["additional_kwargs"]
        return AIMessage(content=content, **kwargs)
    elif msg_type == "ToolMessage":
        kwargs = {}
        if "artifact" in data:
            kwargs["artifact"] = data["artifact"]
        return ToolMessage(
            content=content,
            tool_call_id=data.get("tool_call_id", ""),
            name=data.get("name", ""),
            **kwargs,
        )
    else:
        return HumanMessage(content=content)


def get_history(session_id: str) -> list[BaseMessage]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT messages, updated_at FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return []
        messages_json, updated_at = row
        if time.time() - updated_at > SESSION_TTL_SECONDS:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return []
        return [_deserialize_message(m) for m in json.loads(messages_json)]
    finally:
        conn.close()


def save_history(session_id: str, messages: list[BaseMessage]) -> None:
    trimmed = messages[-MAX_MESSAGES:]
    serialized = json.dumps([_serialize_message(m) for m in trimmed])
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO sessions (session_id, messages, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET messages = ?, updated_at = ?""",
            (session_id, serialized, time.time(), serialized, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def clear_history(session_id: str) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


def cleanup_expired() -> int:
    """Remove all sessions older than TTL. Returns count deleted."""
    cutoff = time.time() - SESSION_TTL_SECONDS
    conn = _connect()
    try:
        cursor = conn.execute("DELETE FROM sessions WHERE updated_at < ?", (cutoff,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
# end AI-generated
