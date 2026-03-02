# AI-generated: Claude Code (claude.ai/code) — FastAPI entry point
import logging
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agent import run_agent
from app.config import settings
from app.memory import clear_history, cleanup_expired
from app.metrics import get_eval_history, metrics
from app.models import ChatRequest, ChatResponse, FeedbackRequest
from app.tools._openemr_client import OpenEMRApiError

logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenEMR Clinical Agent",
    description="Healthcare AI agent with drug interaction checking, patient lookup, and medication management",
    version="0.1.0",
    root_path=settings.root_path,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Record request latency for every endpoint."""
    start = time.perf_counter()
    response = await call_next(request)
    latency = time.perf_counter() - start
    # Only record latency for API requests, skip static files
    if not request.url.path.startswith("/static"):
        metrics.record_request(latency)
    return response


@app.on_event("startup")
async def startup_cleanup():
    """Clean up expired sessions on startup."""
    removed = cleanup_expired()
    if removed > 0:
        logger.info("Cleaned up %d expired sessions on startup", removed)


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        result = await run_agent(req.message, req.session_id)
        return ChatResponse(**result)
    except OpenEMRApiError as e:
        logger.error("OpenEMR API error in chat: %s", e)
        metrics.record_error("openemr_api", str(e))
        raise HTTPException(
            status_code=502,
            detail=f"OpenEMR service error: {e.detail}",
        )
    except httpx.TimeoutException:
        logger.error("External service timeout during chat")
        metrics.record_error("timeout", "External service timeout")
        raise HTTPException(
            status_code=504,
            detail="Request timed out while contacting external services. Please try again.",
        )
    except httpx.ConnectError:
        logger.error("Cannot connect to external service during chat")
        metrics.record_error("connection", "Cannot connect to external service")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to required services. Please check that OpenEMR is running.",
        )
    except Exception:
        logger.exception("Unexpected error in chat endpoint")
        metrics.record_error("unexpected", "Unhandled exception in chat")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again.",
        )


@app.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Record user feedback (thumbs up/down) for a chat response in LangSmith."""
    try:
        from langsmith import Client
        client = Client()
        client.create_feedback(
            run_id=req.run_id,
            key="user_score",
            score=req.score,
            comment=req.comment if req.comment else None,
        )
        return {"status": "ok", "run_id": req.run_id, "score": req.score}
    except Exception as e:
        logger.error("Failed to submit feedback to LangSmith: %s", e)
        metrics.record_error("langsmith", str(e))
        raise HTTPException(status_code=502, detail="Failed to record feedback")


@app.post("/chat/{session_id}/clear")
async def clear_session(session_id: str):
    clear_history(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": settings.xai_model,
    }


@app.get("/metrics")
async def get_metrics():
    """Return agent performance metrics as JSON.

    Includes request latency percentiles, LLM timing, tool call stats,
    token usage, error breakdown, verification trigger counts, and eval history.
    """
    summary = metrics.get_summary()
    summary["eval_history"] = get_eval_history(limit=10)
    return summary


def start():
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    start()
# end AI-generated
