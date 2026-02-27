# AI-generated: Claude Code (claude.ai/code) — request/response models
from pydantic import BaseModel


class PatientContext(BaseModel):
    pid: str | None = None
    pname: str | None = None
    pubpid: str | None = None
    str_dob: str | None = None


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    patient_context: PatientContext | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list[dict] = []
    verification_warnings: list[str] = []
# end AI-generated
