# AI-generated: Claude Code (claude.ai/code) — FastAPI entry point
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.agent import run_agent
from app.config import settings
from app.memory import clear_history
from app.models import ChatRequest, ChatResponse

app = FastAPI(
    title="OpenEMR Clinical Agent",
    description="Healthcare AI agent with drug interaction checking, patient lookup, and medication management",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        result = await run_agent(req.message, req.session_id)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/{session_id}/clear")
async def clear_session(session_id: str):
    clear_history(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "model": settings.xai_model,
    }


def start():
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    start()
# end AI-generated
