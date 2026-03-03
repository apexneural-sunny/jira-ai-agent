"""
main.py — FastAPI app, lifespan, /webhook, /health
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from telegram import Update

import config
from modules.bot import build_application
from modules.logger import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

telegram_app = build_application()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await telegram_app.initialize()
    webhook_url = f"{config.WEBHOOK_URL}/webhook"
    try:
        await telegram_app.bot.set_webhook(url=webhook_url)
        logger.info("Webhook set to %s", webhook_url)
    except Exception as e:
        logger.warning("Could not set webhook (check WEBHOOK_URL): %s", e)
    await telegram_app.start()
    yield
    await telegram_app.stop()
    await telegram_app.shutdown()


app = FastAPI(title="Voice to Jira Bot", lifespan=lifespan)


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok", "bot": telegram_app.bot.username}
