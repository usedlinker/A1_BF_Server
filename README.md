# Bepu (BestFriend) AI Server — A1-3 (Corrected)

FastAPI server for Bepu AI: multilingual chat + TTS. Works on Render.com.

## Endpoints
- `GET /health` → `{status:"ok"}`
- `GET /version`
- `POST /chat` → JSON reply (`reply`, `detected_lang`, `mode` = `openai|fallback`)
- `POST /tts` → MP3 audio stream
