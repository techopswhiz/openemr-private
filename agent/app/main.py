# AI-generated: Claude Code (claude.ai/code) — FastAPI entry point
import logging

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agent import run_agent
from app.config import settings
from app.memory import clear_history, cleanup_expired
from app.models import ChatRequest, ChatResponse
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
        raise HTTPException(
            status_code=502,
            detail=f"OpenEMR service error: {e.detail}",
        )
    except httpx.TimeoutException:
        logger.error("External service timeout during chat")
        raise HTTPException(
            status_code=504,
            detail="Request timed out while contacting external services. Please try again.",
        )
    except httpx.ConnectError:
        logger.error("Cannot connect to external service during chat")
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to required services. Please check that OpenEMR is running.",
        )
    except Exception:
        logger.exception("Unexpected error in chat endpoint")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again.",
        )


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


def start():
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    start()
# end AI-generated
