import uuid
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
conversations: dict[str, dict] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None


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
        return "I'm doing great! How can I help you?"
    if "?" in message:
        return "That's a great question! Let me think about it."
    if any(w in msg_lower for w in ["thanks", "thank you"]):
        return "You're welcome!"
    if any(w in msg_lower for w in ["help", "what can you do"]):
        return "I'm an offline chatbot. You can ask me anything, or type /new to start a new conversation."
    return f"You said: '{message}'. I'm running in offline mode."


def count_tokens(text: str) -> int:
    return len(text.split())


def get_session(session_id: str) -> list[dict]:
    if session_id not in sessions:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return sessions[session_id]


@app.post("/api/auth/google")
async def auth_google():
    user_id = str(uuid.uuid4())
    return {
        "id": user_id,
        "name": "Local User",
        "email": "local@offline.chat",
        "picture": "",
        "conversations": [
            {"id": cid, "title": c["title"]}
            for cid, c in conversations.items()
        ],
    }


@app.get("/api/conversations")
async def list_conversations():
    return {
        "conversations": [
            {"id": cid, "title": c["title"]}
            for cid, c in conversations.items()
        ]
    }


@app.post("/api/conversations")
async def create_conversation():
    cid = str(uuid.uuid4())
    conversations[cid] = {
        "id": cid,
        "title": "New Chat",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
    }
    return {"conversation_id": cid}


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    conv = conversations.get(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@app.post("/api/chat")
async def chat(req: ChatRequest):
    conv_id = req.conversation_id
    session_id = req.session_id

    if conv_id:
        conv = conversations.get(conv_id)
        if not conv:
            conv = {
                "id": conv_id,
                "title": "New Chat",
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            }
            conversations[conv_id] = conv
        history = conv["messages"]
        conv_id = conv["id"]
    else:
        session_id = session_id or str(uuid.uuid4())
        history = get_session(session_id)
        conv_id = session_id

    history.append({"role": "user", "content": req.message})

    try:
        ollama_ok = await check_ollama()
        if ollama_ok:
            reply = await generate_ollama(history)
            source = "ollama"
        else:
            reply = fallback_reply(req.message)
            source = "fallback"
    except Exception:
        reply = fallback_reply(req.message)
        source = "fallback"

    history.append({"role": "assistant", "content": reply})

    if conv_id in conversations:
        title = req.message[:50].strip()
        if len(title) > 30:
            title = title[:30] + "..."
        conversations[conv_id]["title"] = title

    msg_count = sum(1 for m in history if m["role"] in ("user", "assistant"))
    token_count = sum(count_tokens(m["content"]) for m in history)

    return {
        "reply": reply,
        "conversation_id": conv_id,
        "session_id": conv_id if not req.conversation_id else None,
        "messages": msg_count,
        "tokens": token_count,
        "max_tokens": MAX_TOKENS,
        "source": source,
    }


@app.post("/api/reset")
async def reset(req: ResetRequest):
    sessions.pop(req.session_id, None)
    conversations.pop(req.session_id, None)
    return {"status": "ok"}


@app.get("/api/stats/{session_id}")
async def stats(session_id: str):
    history = sessions.get(session_id)
    if not history:
        conv = conversations.get(session_id)
        if conv:
            history = conv["messages"]
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


frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
