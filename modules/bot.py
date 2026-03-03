"""
modules/bot.py — Build and configure the Telegram Application
"""
from telegram.ext import Application, MessageHandler, filters

import config
from modules.handler import handle_text, handle_voice


def build_application() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app
