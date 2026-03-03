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
    add_jira_comment,
    assign_jira_task,
    change_jira_priority,
    create_jira_task,
    delete_jira_task,
    search_jira_tasks,
    update_jira_status,
    update_jira_task,
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

    # Handle clarification requests first
    if intent.needs_clarification and intent.clarification_question:
        await update.message.reply_text(intent.clarification_question)
        return

    if intent.action == "create_task":
        if not intent.summary:
            await update.message.reply_text("Couldn't extract a task title. Please try again.")
            return
        issue_key = await create_jira_task(intent)
        await log_event(user_id, "jira_created", issue_key)
        await update.message.reply_text(
            f"✅ *{issue_key}* created\n"
            f"*{intent.summary}*\n"
            f"Priority: {intent.priority or 'Medium'}\n"
            f"{config.JIRA_URL}/browse/{issue_key}",
            parse_mode="Markdown",
        )

    elif intent.action == "update_task":
        if not intent.issue_key:
            await update.message.reply_text(
                "Please specify the issue key to update.\nExample: Update SCRUM-12 summary to 'New title'"
            )
            return
        if not intent.summary and not intent.description and intent.priority is None:
            await update.message.reply_text(
                "Nothing to update. Please specify what to change.\n"
                "Examples:\n"
                "• Update SCRUM-12 summary to 'New title'\n"
                "• Update SCRUM-5 description to 'New description'"
            )
            return
        await update_jira_task(intent)
        await log_event(user_id, "jira_updated", intent.issue_key)
        changed = []
        if intent.summary:
            changed.append(f"Summary → _{intent.summary}_")
        if intent.description:
            changed.append("Description updated")
        if intent.priority is not None:
            changed.append(f"Priority → _{intent.priority}_")
        await update.message.reply_text(
            f"✅ *{intent.issue_key}* updated\n" + "\n".join(changed) + f"\n{config.JIRA_URL}/browse/{intent.issue_key}",
            parse_mode="Markdown",
        )

    elif intent.action == "assign_task":
        if not intent.issue_key or not intent.assignee_name:
            await update.message.reply_text(
                "Please specify both the issue key and the person to assign to.\n"
                "Example: Assign SCRUM-12 to John"
            )
            return
        display_name = await assign_jira_task(intent.issue_key, intent.assignee_name)
        await log_event(user_id, "jira_assigned", f"{intent.issue_key} → {display_name}")
        await update.message.reply_text(
            f"✅ *{intent.issue_key}* assigned to *{display_name}*\n"
            f"{config.JIRA_URL}/browse/{intent.issue_key}",
            parse_mode="Markdown",
        )

    elif intent.action == "add_comment":
        if not intent.issue_key or not intent.comment_text:
            await update.message.reply_text(
                "Please specify the issue key and the comment.\n"
                "Example: Add comment to SCRUM-12: Looks good, ready for review"
            )
            return
        await add_jira_comment(intent.issue_key, intent.comment_text)
        await log_event(user_id, "jira_commented", intent.issue_key)
        await update.message.reply_text(
            f"💬 Comment added to *{intent.issue_key}*\n{config.JIRA_URL}/browse/{intent.issue_key}",
            parse_mode="Markdown",
        )

    elif intent.action == "change_priority":
        if not intent.issue_key or not intent.priority:
            await update.message.reply_text(
                "Please specify the issue key and new priority.\n"
                "Example: Set SCRUM-12 to High priority"
            )
            return
        await change_jira_priority(intent.issue_key, intent.priority)
        await log_event(user_id, "jira_priority_changed", f"{intent.issue_key} → {intent.priority}")
        await update.message.reply_text(
            f"✅ *{intent.issue_key}* priority set to *{intent.priority}*\n"
            f"{config.JIRA_URL}/browse/{intent.issue_key}",
            parse_mode="Markdown",
        )

    elif intent.action == "change_status":
        if not intent.issue_key or not intent.status_transition:
            await update.message.reply_text(
                "Please specify the issue key and the new status.\n"
                "Example: Move SCRUM-12 to In Progress"
            )
            return
        # Guard: if status_transition looks like a title (long or contains field keywords),
        # GPT likely misrouted an update_task request.
        _status = intent.status_transition.lower()
        _looks_like_title = (
            len(intent.status_transition.split()) > 4
            or any(kw in _status for kw in ("summary", "description", "title", "module", "refactor"))
        )
        if _looks_like_title:
            await update.message.reply_text(
                f"'{intent.status_transition}' doesn't look like a Jira status.\n\n"
                "Valid statuses: *To Do · In Progress · In Review · Done*\n\n"
                "To rename a task, use:\n"
                f"`Update {intent.issue_key} summary: New title here`",
                parse_mode="Markdown",
            )
            return
        new_status = await update_jira_status(intent.issue_key, intent.status_transition)
        await log_event(user_id, "jira_status_updated", f"{intent.issue_key} → {new_status}")
        await update.message.reply_text(
            f"✅ *{intent.issue_key}* moved to *{new_status}*\n"
            f"{config.JIRA_URL}/browse/{intent.issue_key}",
            parse_mode="Markdown",
        )

    elif intent.action == "delete_task":
        if not intent.issue_key:
            await update.message.reply_text(
                "Please specify the issue key to delete.\nExample: Delete SCRUM-5"
            )
            return
        await delete_jira_task(intent.issue_key)
        await log_event(user_id, "jira_deleted", intent.issue_key)
        await update.message.reply_text(f"🗑 *{intent.issue_key}* deleted.", parse_mode="Markdown")

    elif intent.action == "search_issues":
        tasks = await search_jira_tasks(intent.search_filters, intent.project)
        if not tasks:
            await update.message.reply_text("No tasks found matching your filter.")
            return
        lines = [
            f"• *{t['key']}* — {t['summary']}\n"
            f"  Status: {t['status']} | Assignee: {t['assignee']} | Priority: {t['priority']}"
            for t in tasks
        ]
        project_key = intent.project or config.JIRA_PROJECT_KEY
        header = f"📋 *Tasks in {project_key}*"
        if intent.search_filters and intent.search_filters.assignee:
            header += f" · assigned to _{intent.search_filters.assignee}_"
        if intent.search_filters and intent.search_filters.status:
            header += f" · _{intent.search_filters.status}_"
        await update.message.reply_text(
            header + "\n\n" + "\n\n".join(lines),
            parse_mode="Markdown",
        )

    elif intent.action in ("get_analytics", "bulk_operation", "set_notification", "create_automation"):
        await update.message.reply_text(
            f"⚙️ *{intent.action.replace('_', ' ').title()}* is not yet supported.\n"
            "More features coming soon!",
            parse_mode="Markdown",
        )

    elif intent.action == "unrelated":
        await update.message.reply_text(
            intent.clarification_question or "I'm sorry, I can only help with Jira-related tasks."
        )

    else:
        await update.message.reply_text(f"Unknown action: {intent.action}. Please try again.")


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
