import os
import time
from io import BytesIO
from typing import Optional, List

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from langdetect import detect, DetectorFactory
from gtts import gTTS

# Language detection consistency
DetectorFactory.seed = 0

APP_VERSION = os.getenv("BF_APP_VERSION", "A1-3-2025-08-24")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
BF_TEMPERATURE = float(os.getenv("BF_TEMPERATURE", "0.6"))

# Optional OpenAI (gracefully handle if not installed)
_openai_client = None
try:
    if OPENAI_API_KEY:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    _openai_client = None

app = FastAPI(title="Bepu (BestFriend) AI Server", version=APP_VERSION)

# CORS
origins: List[str]
if ALLOWED_ORIGINS == "*":
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


class ChatIn(BaseModel):
    user_id: str = "guest"
    message: str
    target_lang: Optional[str] = ""  # "ko"|"en"|"vi"|""


class ChatOut(BaseModel):
    reply: str
    detected_lang: str
    model: str
    latency_ms: int
    mode: str  # "openai" or "fallback"
    app_version: str = APP_VERSION


class TTSIn(BaseModel):
    text: str
    lang: Optional[str] = ""  # "ko"|"en"|"vi"|""


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/version")
def version():
    return {"version": APP_VERSION}


def _detect_lang(text: str) -> str:
    try:
        code = detect(text)
        # Map some common results to our three-letter set
        if code.startswith("ko"):
            return "ko"
        if code.startswith("vi"):
            return "vi"
        return "en"
    except Exception:
        return "en"


def _translate_hint(lang: str) -> str:
    if lang == "ko":
        return " (한국어로 답변)"
    if lang == "vi":
        return " (Trả lời bằng tiếng Việt)"
    return " (Answer in English)"


def _fallback_reply(msg: str, lang: str) -> str:
    # Very simple friendly fallback template
    if lang == "ko":
        return f"안녕! 난 베프 AI야. 네가 말한 내용은 이렇게 이해했어: “{msg}”. 지금은 간단 모드로 대화 중이야. 더 자세한 답변이 필요하면 OpenAI 키를 설정해줘."
    if lang == "vi":
        return f"Xin chào! Mình là Bepu AI. Mình hiểu bạn nói: “{msg}”. Hiện đang ở chế độ đơn giản. Nếu muốn trả lời chi tiết hơn, hãy cấu hình OPENAI_API_KEY nhé."
    return f"Hi! I'm Bepu AI. I understood: “{msg}”. I'm in a simple fallback mode. For deeper answers, add an OPENAI_API_KEY."


@app.post("/chat", response_model=ChatOut)
def chat(inp: ChatIn):
    t0 = time.time()
    detected = _detect_lang(inp.message)
    target = inp.target_lang.lower().strip() if inp.target_lang else ""
    if target not in ("ko", "en", "vi", ""):
        target = ""

    final_lang = target or detected

    if _openai_client is None:
        reply = _fallback_reply(inp.message, final_lang)
        return ChatOut(
            reply=reply,
            detected_lang=detected,
            model="fallback",
            latency_ms=int((time.time()-t0)*1000),
            mode="fallback",
        )

    # OpenAI path
    prompt = (
        "You are Bepu (BestFriend), a kind, concise friend AI for driving companions. "
        "Speak clearly and warmly. Keep answers short unless asked to elaborate.\n"
        f"User language hint: {final_lang}{_translate_hint(final_lang)}\n"
        f"User: {inp.message}\nAssistant:"
    )

    try:
        resp = _openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are Bepu (BestFriend), an amicable, concise assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=BF_TEMPERATURE,
        )
        text = resp.choices[0].message.content.strip()
        mode = "openai"
        model_used = OPENAI_MODEL
    except Exception as e:
        text = _fallback_reply(inp.message, final_lang)
        mode = "fallback"
        model_used = "fallback"

    return ChatOut(
        reply=text,
        detected_lang=detected,
        model=model_used,
        latency_ms=int((time.time()-t0)*1000),
        mode=mode,
    )


@app.post("/tts")
def tts(inp: TTSIn):
    text = (inp.text or "").strip()
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    # Determine language
    lang = (inp.lang or "").lower().strip()
    if lang not in ("ko", "en", "vi", ""):
        lang = ""
    if not lang:
        lang = _detect_lang(text)
        if lang not in ("ko", "en", "vi"):
            lang = "en"

    # Map to gTTS language codes
    lang_map = {"ko": "ko", "en": "en", "vi": "vi"}
    tts_lang = lang_map.get(lang, "en")

    # Build MP3 in memory
    fp = BytesIO()
    try:
        tts = gTTS(text=text, lang=tts_lang)
        tts.write_to_fp(fp)
        fp.seek(0)
    except Exception as e:
        # Provide a friendly error
        return JSONResponse({"error": f"TTS failed: {str(e)}"}, status_code=500)

    headers = {
        "Content-Disposition": 'inline; filename="voice.mp3"'
    }
    return StreamingResponse(fp, media_type="audio/mpeg", headers=headers)


@app.get("/", response_class=PlainTextResponse)
def root():
    return "Bepu AI Server is running. See /docs for OpenAPI."
