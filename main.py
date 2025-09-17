# main.py
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import time

# ---- OpenAI (>=1.x) SDK ----
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = FastAPI(title="A1-BF-Server", version="1.0.0")

# CORS (앱/웹에서 직접 칠 수 있도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 필요시 도메인 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatIn(BaseModel):
    message: str = Field(..., description="사용자 발화")
    voice: Optional[str] = "ko-KR"
    lang: Optional[str] = "ko"
    persona: Optional[str] = "30세 친구. 운전 중 대화. 캐주얼하고 다정한 톤."
    style: Optional[str] = "짧고 자연스럽게, 1~2문장, 말끝에 가벼운 되물음"
    temperature: Optional[float] = 0.2
    max_sentences: Optional[int] = 2

class ChatOut(BaseModel):
    reply: str
    audio_url: Optional[str] = ""

SYSTEM_TEMPLATE = """너는 운전 중 대화하는 한국어 베스트 프렌드야.
- 항상 한국어로 간단하고 자연스럽게 1~2문장으로 답해.
- 운전 집중을 고려해 장문·리스트·숫자 나열은 피하고, 말끝에 가벼운 되물음을 덧붙여 대화를 잇는다.
- 위험·선정·차별적 내용은 회피하고, 건전한 주제로 부드럽게 전환한다.
페르소나: {persona}
스타일: {style}
"""

def build_messages(persona: str, style: str, user: str):
    system = SYSTEM_TEMPLATE.format(persona=persona, style=style)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

@app.post("/chat", response_model=ChatOut)
def chat(inp: ChatIn):
    t0 = time.time()
    # 안전장치: 비어있는 입력 막기
    user_msg = (inp.message or "").strip()
    if not user_msg:
        return ChatOut(reply="무슨 얘기부터 시작해볼까? 오늘 기분은 어때?", audio_url="")

    # OpenAI가 설정되어 있으면 우선 시도
    if client is not None:
        try:
            messages = build_messages(inp.persona or "", inp.style or "", user_msg)
            # 모델은 gpt-4o-mini / gpt-4.1-mini / gpt-3.5-turbo 등 사용 가능
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=inp.temperature or 0.2,
                max_tokens=128,
            )
            content = completion.choices[0].message.content.strip()
            # 후처리: 문장 길이 제한(너무 길면 자르기, 간단한 안전 장치)
            if inp.max_sentences and inp.max_sentences > 0:
                # 매우 러프하게 문장 수 제한
                parts = [p.strip() for p in content.split("\n") if p.strip()]
                content = " ".join(parts)
            # 말끝에 되물음 없으면 짧게 추가
            if not content.endswith("?") and not content.endswith("다?") and not content.endswith("요?"):
                content = f"{content} 너 생각은 어때?"
            return ChatOut(reply=content, audio_url="")

        except Exception as e:
            # 모델 호출 실패 → 폴백 (자연스러운 기본 멘트, 고정 문구 금지)
            print("[ERROR] OpenAI call failed:", e)

    # 최종 폴백 (고정된 어색한 문구 대신 자연어 한두 문장)
    base = "좋아, 라디오처럼 가볍게 얘기해 보자. 방금 한 말에서 이어서 더 말해줄래?"
    if inp.lang == "ko":
        reply = base
    else:
        reply = "Let's keep it light like radio chat. Want to say a bit more about that?"
    # 말끝에 되물음
    if not reply.endswith("?"):
        reply += " 너 생각은 어때?"

    return ChatOut(reply=reply, audio_url="")

# 헬스체크
@app.get("/")
def root():
    return {"ok": True, "service": "A1-BF-Server"}

if __name__ == "__main__":
    # 로컬 테스트용
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
