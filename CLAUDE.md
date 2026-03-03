# Voice to Jira Bot — Claude Instructions

## Stack
- Python 3.11+
- FastAPI + uvicorn (webhook server)
- python-telegram-bot v20 (async)
- OpenAI Whisper (transcription)
- GPT-4o-mini (intent parsing)
- Jira Python SDK
- aiosqlite (logging)
- rapidfuzz (name matching)
- Pydantic v2 (models)

## Rules — ALWAYS follow these
- Use async/await everywhere, never blocking calls
- One responsibility per module, never mix concerns
- All secrets via config.py using python-dotenv, never hardcode
- Type hints on every function signature
- try/except around every external API call with logging
- Always delete temp files in finally blocks
- Check ALLOWED_USERS at the top of every Telegram handler
- Use Pydantic models for all structured data

## Module Map
- main.py → FastAPI app, lifespan, /webhook, /health
- config.py → env vars only
- modules/bot.py → build Telegram Application
- modules/handler.py → handle_voice(), handle_text()
- modules/transcriber.py → transcribe_voice(path) → str
- modules/intent.py → parse_intent(transcript) → IntentResult
- modules/models.py → Pydantic models
- modules/jira_client.py → create_jira_task(intent) → str
- modules/clarifier.py → get_clarification_question(field) → str
- modules/fuzzy.py → find_assignee(name, users) → dict|None
- modules/rate_limit.py → check_rate_limit(user_id)
- modules/logger.py → init_db(), log_event(...)
