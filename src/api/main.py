"""FastAPI + SSE for PriceCheck chat UI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Generator, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.agent.agent import ReActAgent
from src.chatbot.chatbot_baseline import run_chatbot
from src.core.llm_factory import get_llm_from_env
from src.tools import TOOL_SPECS

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
STATIC_CHAT = ROOT / "static" / "chat" / "index.html"

app = FastAPI(
    title="PriceCheck Agent API",
    description="ReAct agent + chatbot baseline with SSE streaming",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    mode: Literal["agent", "chatbot"] = "agent"
    persist_catalog: bool = True


def _sse_event(event_type: str, data: Dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _stream_agent(message: str, persist_catalog: bool) -> Generator[str, None, None]:
    llm = get_llm_from_env()
    agent = ReActAgent(
        llm=llm,
        tools=TOOL_SPECS,
        persist_catalog_updates=persist_catalog,
    )
    for event in agent.run_stream(message):
        ev_type = event.pop("type", "message")
        yield _sse_event(ev_type, event)


def _stream_chatbot(message: str) -> Generator[str, None, None]:
    llm = get_llm_from_env()
    yield _sse_event("chatbot_start", {"model": llm.model_name})
    yield _sse_event("llm_start", {"step": 0})
    try:
        answer = run_chatbot(llm, message)
        yield _sse_event("llm_done", {"step": 0})
        yield _sse_event("final_answer", {"step": 0, "text": answer})
        yield _sse_event("done", {"status": "final_answer"})
    except Exception as e:
        yield _sse_event("error", {"message": str(e)})
        yield _sse_event("done", {"status": "error"})


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "pricecheck-api"}


@app.get("/")
def chat_page() -> FileResponse:
    if not STATIC_CHAT.exists():
        raise HTTPException(404, "Chat UI not found")
    return FileResponse(STATIC_CHAT)


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    message = req.message.strip()
    if not message:
        raise HTTPException(400, "message is required")

    if req.mode == "chatbot":
        generator = _stream_chatbot(message)
    else:
        generator = _stream_agent(message, req.persist_catalog)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
