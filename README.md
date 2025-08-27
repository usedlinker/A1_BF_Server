# Bepu (BestFriend) AI Server — A1-3

FastAPI server for Bepu AI: multilingual chat + TTS. Works on Render.com.

## Endpoints
- `GET /health` → `{status:"ok"}`
- `GET /version`
- `POST /chat` → JSON reply (`reply`, `detected_lang`, `mode`)
- `POST /tts` → MP3 audio stream

## Quick Start (Local)
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
curl -i http://127.0.0.1:8000/health
