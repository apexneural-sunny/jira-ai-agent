# Voice to Jira Bot

A Telegram bot that converts **voice notes and text messages** into Jira actions using OpenAI Whisper (transcription) and GPT-4o-mini (intent parsing).

---

## Stack

| Layer | Technology |
|---|---|
| API Server | FastAPI + Uvicorn |
| Telegram | python-telegram-bot v20 (webhook mode) |
| Transcription | OpenAI Whisper (`whisper-1`) |
| Intent Parsing | OpenAI GPT-4o-mini |
| Jira | Jira Python SDK |
| Fuzzy Matching | rapidfuzz |
| Storage | aiosqlite (event log + rate limiting) |
| Config | python-dotenv + Pydantic v2 |

---

## Setup

### 1. Clone & create virtualenv

```bash
cd /Applications/MAMP/htdocs/automation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure `.env`

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
WEBHOOK_URL=https://your-ngrok-or-domain.ngrok-free.app

OPENAI_API_KEY=your_openai_api_key

JIRA_URL=https://yourorg.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=SCRUM

ALLOWED_TELEGRAM_USERS=123456789,987654321
```

### 3. Start the server

```bash
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Expose via ngrok (local dev)

```bash
ngrok http 8000
```

Update `WEBHOOK_URL` in `.env` with the ngrok HTTPS URL, then restart the server.

---

## Bot Commands

Send any of these as **text** or a **voice note** in Telegram.

**Supported issue types:** `Task` · `Bug` · `Story` · `Epic` · `Subtask`
**Supported priorities:** `Highest` · `High` · `Medium` · `Low` · `Lowest`

---

### Create a Task

```
Create a task for fixing the login bug
Create a story for the user profile page
Add a bug for payment gateway timeout
Create an urgent task: migrate database to PostgreSQL
Create a high priority bug assigned to John
Create a story with description "allow users to reset password"
```

---

### Update a Task

```
Update SCRUM-12 summary: Refactor auth module
Update SCRUM-5 description: needs more details
Rename SCRUM-8 to Fix login bug
Edit SCRUM-3 description: updated details here
```

> Use a colon (`:`) to separate the field from the new value — this avoids ambiguity with status changes.

---

### Assign a Task

```
Assign SCRUM-12 to John
Assign SCRUM-5 to Sarah
Give SCRUM-9 to Mike
```

> Assignee is matched by name — partial names work (e.g. "John" matches "John Smith").

---

### Add a Comment

```
Add comment to SCRUM-12: Looks good, ready for review
Comment on SCRUM-5: Blocked waiting for design assets
Add a note to SCRUM-9: Fixed in latest build
Leave a comment on SCRUM-3: Will review tomorrow
```

---

### Change Priority

```
Set SCRUM-12 to High priority
Mark SCRUM-5 as urgent
Change priority of SCRUM-8 to Lowest
Make SCRUM-3 high priority
```

**Priority levels:** `Highest` · `High` · `Medium` · `Low` · `Lowest`

---

### Change Status

```
Move SCRUM-12 to In Progress
Mark SCRUM-8 as Done
Set SCRUM-3 to In Review
Move SCRUM-15 to To Do
Close SCRUM-7
Reopen SCRUM-4
```

> Status names are fuzzy-matched against available Jira transitions, so variations like "in progress", "done", "review" all work.

---

### Search / List Tasks

```
Show my tasks
List tasks assigned to Sarah
Show high priority bugs
Find all in-progress stories
List tasks created this week
Show open tasks for John
Find all critical bugs in the SCRUM project
Show tasks due next Friday
```

**Supported status filters:** `Backlog` · `To Do` · `In Progress` · `In Review` · `Done`

> **Backlog** = issues not yet assigned to any sprint (`sprint is EMPTY`).

---

### Delete a Task

```
Delete SCRUM-5
Remove SCRUM-12
Trash SCRUM-9
```

> **Warning:** Deletion is permanent and cannot be undone. The bot will ask for the issue key if not provided.

---

### Unrelated Input

Any non-Jira question (weather, jokes, general knowledge, etc.) will be declined:
> "I'm sorry, I can only help with Jira-related tasks."

---

### Coming Soon

The following actions are parsed but not yet fully implemented:

| Action | Example |
|---|---|
| Analytics | "Show project velocity", "Give me a summary of SCRUM" |
| Bulk operations | "Mark all John's tasks as Done", "Reassign all open bugs to Sarah" |
| Notifications | "Notify me when SCRUM-12 changes status" |
| Automation | "When a bug is created, assign it to John" |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhook` | Telegram webhook receiver |
| `GET` | `/health` | Health check — returns bot username |

---

## Rate Limiting

Each user is limited to **10 requests per minute**. Exceeding this returns:
> "Rate limit exceeded. Please wait a moment."

---

## Project Structure

```
jira-ai-agent/
├── main.py                  # FastAPI app, lifespan, /webhook, /health
├── config.py                # Environment variable loading
├── requirements.txt
├── .env                     # Secrets (never commit)
├── .env.example             # Template for environment variables
├── .gitignore
├── CLAUDE.md                # Claude Code instructions
└── modules/
    ├── bot.py               # Telegram Application builder
    ├── handler.py           # handle_voice(), handle_text(), _dispatch()
    ├── intent.py            # GPT-4o-mini intent parsing → IntentResult
    ├── models.py            # Pydantic models (IntentResult, SearchFilters, …)
    ├── jira_client.py       # Jira API: create / update / assign / comment /
    │                        #           priority / status / search / delete
    ├── transcriber.py       # OpenAI Whisper transcription
    ├── logger.py            # aiosqlite event logging
    ├── rate_limit.py        # Sliding window rate limiter (10 req/min)
    ├── fuzzy.py             # rapidfuzz name matching
    └── clarifier.py         # Clarification question strings
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | From [@BotFather](https://t.me/BotFather) |
| `WEBHOOK_URL` | Yes | Public HTTPS URL pointing to this server |
| `OPENAI_API_KEY` | Yes | OpenAI API key (for Whisper + GPT-4o-mini) |
| `JIRA_URL` | Yes | Your Atlassian URL e.g. `https://org.atlassian.net` |
| `JIRA_EMAIL` | Yes | Atlassian account email |
| `JIRA_API_TOKEN` | Yes | Jira API token (from Atlassian account settings) |
| `JIRA_PROJECT_KEY` | Yes | Project key e.g. `SCRUM` |
| `ALLOWED_TELEGRAM_USERS` | Yes | Comma-separated Telegram user IDs |
| `PORT` | No | Server port (default: `8000`) |
