import asyncio
import uuid
import time
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Offline Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_BASE = "http://localhost:11434"
MODEL = "qwen2.5:0.5b"
MAX_TOKENS = 512
SYSTEM_PROMPT = "You are a helpful, friendly assistant. Keep responses concise."

sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ResetRequest(BaseModel):
    session_id: str


async def check_ollama() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def generate_ollama(messages: list[dict]) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": MAX_TOKENS},
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"].strip()


def fallback_reply(message: str) -> str:
    msg_lower = message.lower()

    if any(w in msg_lower for w in ["hello", "hi", "hey", "yo"]):
        return "Hi there! How can I help you today?"
    if any(w in msg_lower for w in ["bye", "goodbye", "see you"]):
        return "Goodbye! Feel free to come back anytime."
    if any(w in msg_lower for w in ["how are you", "how's it going"]):
        return "I'm doing great, thanks for asking! How can I assist you?"
    if "?" in message:
        return "That's a great question! Unfortunately, I'm running in offline mode without a full language model loaded."
    if any(w in msg_lower for w in ["thanks", "thank you"]):
        return "You're welcome! Happy to help."
    if any(w in msg_lower for w in ["help", "what can you do"]):
        return "I'm an offline chatbot. You can ask me questions, chat with me, or type /new to start a new conversation."

    return f"I received your message: '{message}'. I'm running in offline mode. To get more intelligent responses, make sure Ollama is running with a model loaded."


def count_tokens(text: str) -> int:
    return len(text.split())


def get_session(session_id: str) -> list[dict]:
    if session_id not in sessions:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return sessions[session_id]


@app.post("/api/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    history = get_session(session_id)

    history.append({"role": "user", "content": req.message})

    try:
        ollama_ok = await check_ollama()
        if ollama_ok:
            reply = await generate_ollama(history)
            source = "ollama"
        else:
            reply = fallback_reply(req.message)
            source = "fallback"
    except Exception as e:
        reply = fallback_reply(req.message)
        source = "fallback"

    history.append({"role": "assistant", "content": reply})

    msg_count = sum(1 for m in history if m["role"] in ("user", "assistant"))
    token_count = sum(count_tokens(m["content"]) for m in history)

    return {
        "reply": reply,
        "session_id": session_id,
        "messages": msg_count,
        "tokens": token_count,
        "max_tokens": MAX_TOKENS,
        "source": source,
    }


@app.post("/api/reset")
async def reset(req: ResetRequest):
    sessions.pop(req.session_id, None)
    return {"status": "ok"}


@app.get("/api/stats/{session_id}")
async def stats(session_id: str):
    history = sessions.get(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    msg_count = sum(1 for m in history if m["role"] in ("user", "assistant"))
    token_count = sum(count_tokens(m["content"]) for m in history)
    return {
        "messages": msg_count,
        "tokens": token_count,
        "max_tokens": MAX_TOKENS,
    }


@app.get("/health")
async def health():
    ollama_ok = await check_ollama()
    return {
        "status": "ok",
        "ollama": ollama_ok,
        "model": MODEL if ollama_ok else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
