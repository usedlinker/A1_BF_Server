# Bepu (BestFriend) AI Server — A1-3 (Fixed)

FastAPI server for Bepu AI: multilingual chat + TTS. Works on Render.com.

## Endpoints
- `GET /health` → `{status:"ok"}`
- `GET /version`
- `POST /chat` → JSON reply (`reply`, `detected_lang`, `mode` = `openai|fallback`)
- `POST /tts` → MP3 audio stream

## Quick Start (Local)
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
curl -i http://127.0.0.1:8000/health
```

## Render Deploy
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Env (optional): `ALLOWED_ORIGINS`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `BF_TEMPERATURE`, `BF_APP_VERSION`

## Notes
- Without `OPENAI_API_KEY`, `/chat` runs in fallback mode.
- `/tts` uses **gTTS 2.5.4** (latest supported).
- CORS is controlled via `ALLOWED_ORIGINS` (default `*`).

## License
MIT
