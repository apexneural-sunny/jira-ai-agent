"""
modules/handler.py — Telegram update handlers: handle_voice(), handle_text()
"""
import logging
import os
import tempfile

from telegram import Update
from telegram.ext import ContextTypes

import config
from modules.intent import parse_intent
from modules.jira_client import (
    assign_jira_task,
    create_jira_task,
    delete_jira_task,
    list_jira_tasks,
    update_jira_status,
)
from modules.logger import log_event
from modules.models import IntentResult
from modules.rate_limit import check_rate_limit
from modules.transcriber import transcribe_voice

logger = logging.getLogger(__name__)


def _is_allowed(user_id: int) -> bool:
    return user_id in config.ALLOWED_TELEGRAM_USERS


async def _dispatch(update: Update, intent: IntentResult, user_id: int) -> None:
    """Route to the correct Jira operation based on intent.action."""

    if intent.action == "assign":
        if not intent.issue_key or not intent.assignee:
            await update.message.reply_text(
                "Please specify both the issue key and the person to assign to.\n"
                "Example: Assign SCRUM-12 to John"
            )
            return
        display_name = await assign_jira_task(intent.issue_key, intent.assignee)
        await log_event(user_id, "jira_assigned", f"{intent.issue_key} → {display_name}")
        await update.message.reply_text(
            f"✅ *{intent.issue_key}* assigned to *{display_name}*\n"
            f"{config.JIRA_URL}/browse/{intent.issue_key}",
            parse_mode="Markdown",
        )

    elif intent.action == "delete":
        if not intent.issue_key:
            await update.message.reply_text(
                "Please specify the issue key to delete.\n"
                "Example: Delete SCRUM-5"
            )
            return
        await delete_jira_task(intent.issue_key)
        await log_event(user_id, "jira_deleted", intent.issue_key)
        await update.message.reply_text(f"🗑 *{intent.issue_key}* deleted.", parse_mode="Markdown")

    elif intent.action == "list":
        tasks = await list_jira_tasks(intent.assignee, intent.status_filter)
        if not tasks:
            await update.message.reply_text("No tasks found matching your filter.")
            return
        lines = [
            f"• *{t['key']}* — {t['summary']}\n"
            f"  Status: {t['status']} | Assignee: {t['assignee']} | Priority: {t['priority']}"
            for t in tasks
        ]
        header = f"📋 *Tasks in {config.JIRA_PROJECT_KEY}*"
        if not intent.assignee:
            header += " · _created by me_"
        else:
            header += f" · assigned to _{intent.assignee}_"
        if intent.status_filter:
            header += f" · _{intent.status_filter}_"
        await update.message.reply_text(
            header + "\n\n" + "\n\n".join(lines),
            parse_mode="Markdown",
        )

    elif intent.action == "update_status":
        if not intent.issue_key or not intent.status:
            await update.message.reply_text(
                "Please specify the issue key and the new status.\n"
                "Example: Move SCRUM-12 to In Progress"
            )
            return
        new_status = await update_jira_status(intent.issue_key, intent.status)
        await log_event(user_id, "jira_status_updated", f"{intent.issue_key} → {new_status}")
        await update.message.reply_text(
            f"✅ *{intent.issue_key}* moved to *{new_status}*\n"
            f"{config.JIRA_URL}/browse/{intent.issue_key}",
            parse_mode="Markdown",
        )

    else:  # create
        if not intent.title:
            await update.message.reply_text("Couldn't extract a task title. Please try again.")
            return
        issue_key = await create_jira_task(intent)
        await log_event(user_id, "jira_created", issue_key)
        await update.message.reply_text(
            f"✅ *{issue_key}* created\n"
            f"*{intent.title}*\n"
            f"Priority: {intent.priority or 'Medium'}\n"
            f"{config.JIRA_URL}/browse/{issue_key}",
            parse_mode="Markdown",
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not _is_allowed(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    if not await check_rate_limit(user_id):
        await update.message.reply_text("Rate limit exceeded. Please wait a moment.")
        return

    await update.message.reply_text("Got your voice note, transcribing...")

    ogg_path: str | None = None
    try:
        voice = update.message.voice
        tg_file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            ogg_path = tmp.name
        await tg_file.download_to_drive(ogg_path)

        transcript = await transcribe_voice(ogg_path)
        await log_event(user_id, "transcribed", transcript[:200])
        await update.message.reply_text(f'Transcript: "{transcript}"')

        intent = await parse_intent(transcript)
        await _dispatch(update, intent, user_id)

    except Exception as e:
        logger.error("handle_voice error for user %s: %s", user_id, e)
        await log_event(user_id, "error", str(e))
        await update.message.reply_text(f"Something went wrong: {e}")

    finally:
        if ogg_path and os.path.exists(ogg_path):
            os.remove(ogg_path)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not _is_allowed(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    if not await check_rate_limit(user_id):
        await update.message.reply_text("Rate limit exceeded. Please wait a moment.")
        return

    text = update.message.text or ""
    if not text.strip():
        return

    try:
        intent = await parse_intent(text)
        await _dispatch(update, intent, user_id)

    except Exception as e:
        logger.error("handle_text error for user %s: %s", user_id, e)
        await log_event(user_id, "error", str(e))
        await update.message.reply_text(f"Something went wrong: {e}")
