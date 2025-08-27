import os
import io
import time
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel

try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    _LANGDETECT = True
except Exception:
    _LANGDETECT = False

try:
    from openai import OpenAI
    _OPENAI_IMPORTED = True
except Exception:
    _OPENAI_IMPORTED = False

from gtts import gTTS

APP_VERSION = os.getenv("BF_APP_VERSION", "A1-3-2025-08-27")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
BF_TEMPERATURE = float(os.getenv("BF_TEMPERATURE", "0.6"))

# Create FastAPI app (Uvicorn loads main:app)
app = FastAPI(title="Bepu (BestFriend) AI Server", version=APP_VERSION)

# CORS
origins: List[str]
if ALLOWED_ORIGINS.strip() == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_openai_client = None
if _OPENAI_IMPORTED and OPENAI_API_KEY:
    try:
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        _openai_client = None


class HistoryItem(BaseModel):
    role: str
    content: str

class ChatIn(BaseModel):
    user_id: str = "guest"
    message: str
    history: Optional[List[HistoryItem]] = None
    target_lang: Optional[str] = None

class ChatOut(BaseModel):
    reply: str
    detected_lang: str
    model: str
    mode: str
    latency_ms: int
    version: str = APP_VERSION

class TTSIn(BaseModel):
    text: str
    lang: Optional[str] = None


def detect_lang(text: str) -> str:
    if _LANGDETECT:
        try:
            code = detect(text)
            if code.startswith("ko"):
                return "ko"
            if code.startswith("vi"):
                return "vi"
            return "en"
        except Exception:
            return "en"
    return "en"

def translate_hint(lang: str) -> str:
    return {"ko": " (한국어)", "vi": " (Tiếng Việt)", "en": " (English)"}.get(lang, " (English)")

def fallback_reply(msg: str, lang: str) -> str:
    if lang == "ko":
        return f"안녕! 베프 AI야. "{msg}" 이렇게 이해했어. 지금은 간단 모드로 답해."
    if lang == "vi":
        return f"Xin chào! Mình là Bepu AI. Mình hiểu: "{msg}". Hiện đang ở chế độ đơn giản."
    return f"Hi! I'm Bepu AI. I understood: "{msg}". Running in simple mode."


@app.get("/", response_class=PlainTextResponse)
def root():
    return "Bepu AI Server is running. See /docs for OpenAPI."

@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}

@app.get("/version")
def version():
    return {"version": APP_VERSION}

@app.post("/chat", response_model=ChatOut)
def chat(inp: ChatIn):
    t0 = time.time()
    lang = inp.target_lang or detect_lang(inp.message)

    # Try OpenAI first
    if _openai_client is not None:
        try:
            msgs = [
                {"role": "system", "content": "You are Bepu (BestFriend), a kind and concise assistant."},
                {"role": "user", "content": f"User language: {lang}{translate_hint(lang)}\nUser: {inp.message}\nAssistant:"},
            ]
            resp = _openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=msgs,
                temperature=BF_TEMPERATURE,
            )
            reply = resp.choices[0].message.content.strip()
            return ChatOut(
                reply=reply,
                detected_lang=lang,
                model=OPENAI_MODEL,
                mode="openai",
                latency_ms=int((time.time()-t0)*1000),
            )
        except Exception:
            pass

    reply = fallback_reply(inp.message, lang)
    return ChatOut(
        reply=reply,
        detected_lang=lang,
        model="fallback",
        mode="fallback",
        latency_ms=int((time.time()-t0)*1000),
    )

@app.post("/tts")
def tts(inp: TTSIn):
    text = (inp.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    lang = (inp.lang or "").strip().lower()
    if lang not in {"ko", "en", "vi"}:
        lang = detect_lang(text)
        if lang not in {"ko", "en", "vi"}:
            lang = "en"

    buf = io.BytesIO()
    try:
        gTTS(text=text, lang=lang).write_to_fp(buf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")
    buf.seek(0)
    return StreamingResponse(buf, media_type="audio/mpeg", headers={"Content-Disposition": 'inline; filename="voice.mp3"'})
