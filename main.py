from fastapi import FastAPI
from pydantic import BaseModel
import openai
import os
from fastapi.middleware.cors import CORSMiddleware

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str

@app.post("/chat")
async def chat_with_bef(message: Message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "넌 '베프'라는 이름의 밝고 다정한 AI 친구야. 유저가 외롭거나 궁금한 게 있을 때 따뜻하게 이야기해줘."},
                {"role": "user", "content": message.message}
            ],
            temperature=0.8
        )
        reply = response['choices'][0]['message']['content']
        return {"reply": reply}
    except Exception as e:
        return {"error": str(e)}
