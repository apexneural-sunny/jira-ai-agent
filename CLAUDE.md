# Voice to Jira Bot — Claude Instructions

## Stack
- Python 3.11+
- FastAPI + uvicorn (webhook server)
- python-telegram-bot v20 (async)
- OpenAI Whisper (transcription)
- GPT-4o-mini (intent parsing)
- Jira Python SDK
- aiosqlite (logging)
- rapidfuzz (fuzzy status matching)
- Pydantic v2 (models + validators)

## Rules — ALWAYS follow these
- Use async/await everywhere, never blocking calls
- One responsibility per module, never mix concerns
- All secrets via config.py using python-dotenv, never hardcode
- Type hints on every function signature
- try/except around every external API call with logging
- Always delete temp files in finally blocks
- Check ALLOWED_USERS at the top of every Telegram handler
- Use Pydantic models for all structured data

## Intent Actions
The bot supports these actions (returned by GPT-4o-mini via parse_intent):
- `create_task` — create a new Jira issue
- `update_task` — update summary/description of an existing issue
- `assign_task` — assign an issue to a user by name
- `add_comment` — add a comment to an existing issue
- `change_priority` — update priority of an existing issue
- `change_status` — transition issue to a new status (fuzzy-matched)
- `delete_task` — permanently delete an issue
- `search_issues` — JQL search with SearchFilters
- `get_analytics` — project analytics (not yet implemented)
- `bulk_operation` — bulk field updates (not yet implemented)
- `set_notification` — watch/subscribe to issues (not yet implemented)
- `create_automation` — create automation rules (not yet implemented)
- `unrelated` — non-Jira input, bot declines politely

## Intent Parsing Rules (system prompt design)
- Prompt uses KEYWORD PRIORITY RULES (A–I), checked in order — first match wins
- Rule A: "summary"/"description"/"title" + issue key → always update_task (never change_status)
- Rule B: "comment"/"note" + issue key → add_comment
- Rule C: "priority"/"urgent"/"critical" + issue key → change_priority
- Rule F: known status words (Done, In Progress, etc.) → change_status
- Few-shot examples at end of prompt prevent misrouting (e.g. "update X summary to Y" being treated as a status transition)
- `priority` field defaults to null (not "Medium") — prevents silent overwrites
- `missing_fields` has a Pydantic validator to coerce null → [] (prevents ValidationError)

## Key Bugs Fixed
- `priority: Optional[str] = None` — was "Medium", caused silent priority overwrites on every update_task
- `if intent.priority is not None` — was `if intent.priority:`, so "Medium" default always triggered
- `missing_fields` validator — GPT returning null instead of [] caused Pydantic ValidationError on every call
- System prompt placeholder strings in search_filters — now all set to null to prevent GPT filling garbage
- change_status guard in handler — detects misrouted update_task requests (status_transition > 4 words or contains field keywords) and shows a helpful message instead of "No transition found"

## Module Map
- main.py → FastAPI app, lifespan, /webhook, /health
- config.py → env vars only
- modules/bot.py → build Telegram Application
- modules/handler.py → handle_voice(), handle_text(), _dispatch()
- modules/transcriber.py → transcribe_voice(path) → str
- modules/intent.py → parse_intent(transcript) → IntentResult (GPT-4o-mini with keyword priority rules + few-shot examples)
- modules/models.py → Pydantic models: IntentResult, SearchFilters, BulkOperationFilters, AutomationRule
- modules/jira_client.py → create_jira_task, update_jira_task, assign_jira_task, add_jira_comment, change_jira_priority, update_jira_status, search_jira_tasks, delete_jira_task
- modules/clarifier.py → get_clarification_question(field) → str
- modules/fuzzy.py → find_assignee(name, users) → dict|None
- modules/rate_limit.py → check_rate_limit(user_id)
- modules/logger.py → init_db(), log_event(...)

## IntentResult Fields
- action, summary, description, project, issue_type, priority (null by default), story_points
- assignee_name, issue_key
- comment_text (add_comment), status_transition (change_status)
- needs_clarification, missing_fields (list, validated), clarification_question
- search_filters (SearchFilters), analytics_type
- bulk_operation_filters (BulkOperationFilters), bulk_operation_action
- notification_type, notification_target
- automation_rule (AutomationRule)

## Jira SDK Notes
- All Jira calls run via asyncio.to_thread (sync SDK wrapped in async)
- Issue update: jira.issue(key).update(fields={...})
- Status transition: fuzzy-matched with rapidfuzz against available transitions
- Comment: jira.add_comment(issue_key, body)
- Priority uses {"priority": {"name": "High"}} field format
- Project defaults to config.JIRA_PROJECT_KEY if not specified in intent
