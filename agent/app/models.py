# AI-generated: Claude Code (claude.ai/code) — request/response models
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ReasoningStep(BaseModel):
    """A single step in the agent's chain-of-thought reasoning."""
    action: str = Field(description="What the agent did (e.g., 'Looked up patient', 'Checked drug interactions')")
    result: str = Field(description="What the agent found or concluded")


class Citation(BaseModel):
    """A source citation for a clinical claim."""
    claim: str = Field(description="The specific clinical assertion")
    source: str = Field(description="Where this information came from (e.g., 'NLM RxNorm', 'FDA Drug Label', 'OpenEMR patient record')")


class Finding(BaseModel):
    """A discrete clinical finding from the agent's analysis."""
    category: str = Field(description="Type of finding: 'interaction', 'allergy_conflict', 'info', 'warning'")
    severity: str | None = Field(default=None, description="Severity level if applicable: 'high', 'moderate', 'low'")
    summary: str = Field(description="One-line summary of the finding")
    details: str = Field(default="", description="Additional context or explanation")


class StructuredResponse(BaseModel):
    """Structured clinical response from the agent's analysis."""
    summary: str = Field(description="1-2 sentence plain-language summary of the response")
    reasoning: list[ReasoningStep] = Field(default_factory=list, description="Chain-of-thought reasoning steps")
    findings: list[Finding] = Field(default_factory=list, description="Discrete clinical findings")
    citations: list[Citation] = Field(default_factory=list, description="Sources backing clinical claims")


class ChatResponse(BaseModel):
    response: str
    structured: StructuredResponse | None = None
    session_id: str
    tool_calls: list[dict] = []
    verification_warnings: list[str] = []
    run_id: str = ""


class FeedbackRequest(BaseModel):
    run_id: str = Field(description="The LangSmith run ID from the chat response")
    score: int = Field(description="1 for thumbs up, 0 for thumbs down", ge=0, le=1)
    comment: str = Field(default="", description="Optional user comment")
# end AI-generated
