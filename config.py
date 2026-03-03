"""
config.py — Environment variable loading via python-dotenv
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL: str = os.environ["WEBHOOK_URL"]
PORT: int = int(os.environ.get("PORT", 8000))

OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]

JIRA_URL: str = os.environ["JIRA_URL"]
JIRA_EMAIL: str = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN: str = os.environ["JIRA_API_TOKEN"]
JIRA_PROJECT_KEY: str = os.environ.get("JIRA_PROJECT_KEY", "PROJ")

ALLOWED_TELEGRAM_USERS: set[int] = {
    int(uid.strip())
    for uid in os.environ.get("ALLOWED_TELEGRAM_USERS", "").split(",")
    if uid.strip().isdigit()
}
