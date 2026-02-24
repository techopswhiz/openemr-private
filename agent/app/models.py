# AI-generated: Claude Code (claude.ai/code) — request/response models
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list[dict] = []
    verification_warnings: list[str] = []
# end AI-generated
