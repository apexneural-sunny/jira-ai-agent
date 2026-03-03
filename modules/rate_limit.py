"""
modules/rate_limit.py — Rate limiting: check_rate_limit(user_id)
"""
import logging
from datetime import datetime, timedelta, timezone

import aiosqlite

from modules.logger import DB_PATH

RATE_LIMIT = 10  # max requests per minute
logger = logging.getLogger(__name__)


async def check_rate_limit(user_id: int) -> bool:
    """Return True if the user is within the rate limit, False if exceeded."""
    window_start = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM events WHERE user_id = ? AND created_at > ?",
                (user_id, window_start),
            ) as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0
        return count < RATE_LIMIT
    except Exception as e:
        logger.error("check_rate_limit failed: %s", e)
        return True  # fail open
