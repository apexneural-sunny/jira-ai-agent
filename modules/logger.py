"""
modules/logger.py — SQLite event logging: init_db(), log_event(...)
"""
import logging
from datetime import datetime, timezone

import aiosqlite

DB_PATH = "bot_events.db"
logger = logging.getLogger(__name__)


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                event_type  TEXT,
                detail      TEXT,
                created_at  TEXT
            )
        """)
        await db.commit()


async def log_event(user_id: int, event_type: str, detail: str = "") -> None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO events (user_id, event_type, detail, created_at) VALUES (?, ?, ?, ?)",
                (user_id, event_type, detail, datetime.now(timezone.utc).isoformat()),
            )
            await db.commit()
    except Exception as e:
        logger.error("log_event failed: %s", e)
