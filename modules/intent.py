"""
modules/intent.py — Intent parsing: parse_intent(transcript) -> IntentResult
"""
import json
import logging

from openai import AsyncOpenAI

import config
from modules.models import IntentResult

logger = logging.getLogger(__name__)
_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

_SYSTEM_PROMPT = """You are an assistant that extracts Jira task actions from voice or text input.

Determine the action:
- "create" → user wants to create a new task
- "assign" → user wants to assign an existing task to someone
- "delete" → user wants to delete/remove an existing task
- "list" → user wants to see a list of tasks (optionally filtered by assignee)
- "update_status" → user wants to change the status/column of an existing task

Return a JSON object with ONLY the relevant fields for the action:

For "create":
  title (str, required), description (str, optional), assignee (str, optional),
  priority (str, optional: Low|Medium|High|Critical), story_points (int, optional),
  issue_type (str: Task|Bug|Story|Epic)

For "assign":
  issue_key (str, required), assignee (str, required)

For "delete":
  issue_key (str, required)

For "list":
  assignee (str, optional — filter by this person's name)
  status_filter (str, optional — filter by status e.g. "Backlog", "In Progress", "To Do", "In Review")

For "update_status":
  issue_key (str, required), status (str, required — e.g. "In Progress", "Done", "To Do")

Always include: action (str, required)

Examples:
- "Create a bug for the login page" → {"action":"create","title":"Bug for login page","issue_type":"Bug"}
- "Assign SCRUM-12 to John" → {"action":"assign","issue_key":"SCRUM-12","assignee":"John"}
- "Delete SCRUM-5" → {"action":"delete","issue_key":"SCRUM-5"}
- "Show my tasks" → {"action":"list"}
- "List tasks assigned to Sarah" → {"action":"list","assignee":"Sarah"}
- "Show backlog tasks" → {"action":"list","status_filter":"Backlog"}
- "List in-progress tasks for John" → {"action":"list","assignee":"John","status_filter":"In Progress"}
- "Move SCRUM-12 to In Progress" → {"action":"update_status","issue_key":"SCRUM-12","status":"In Progress"}
- "Mark SCRUM-8 as Done" → {"action":"update_status","issue_key":"SCRUM-8","status":"Done"}

Return only valid JSON — no extra text."""


async def parse_intent(transcript: str) -> IntentResult:
    """Parse a transcript into structured Jira task fields using GPT-4o-mini."""
    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        return IntentResult(**data)
    except Exception as e:
        logger.error("parse_intent failed: %s", e)
        raise
