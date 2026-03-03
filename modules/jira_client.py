"""
modules/jira_client.py — Jira integration: create_jira_task(intent) -> str
"""
import asyncio
import logging

from jira import JIRA

import config
from modules.models import IntentResult

logger = logging.getLogger(__name__)


def _get_client() -> JIRA:
    return JIRA(
        server=config.JIRA_URL,
        basic_auth=(config.JIRA_EMAIL, config.JIRA_API_TOKEN),
    )


def _create_sync(intent: IntentResult) -> str:
    """Synchronous Jira issue creation (run via asyncio.to_thread)."""
    jira = _get_client()

    fields: dict = {
        "project": {"key": config.JIRA_PROJECT_KEY},
        "summary": intent.title,
        "issuetype": {"name": intent.issue_type},
        "priority": {"name": intent.priority or "Medium"},
    }
    if intent.description:
        fields["description"] = intent.description
    if intent.story_points is not None:
        fields["story_points"] = intent.story_points

    issue = jira.create_issue(fields=fields)

    if intent.assignee:
        try:
            users = jira.search_users(query=intent.assignee)
            if users:
                jira.assign_issue(issue, users[0].accountId)
        except Exception as e:
            logger.warning("Could not assign '%s': %s", intent.assignee, e)

    return issue.key


async def create_jira_task(intent: IntentResult) -> str:
    """Create a Jira issue from *intent* and return its issue key (e.g. 'SCRUM-42')."""
    try:
        return await asyncio.to_thread(_create_sync, intent)
    except Exception as e:
        logger.error("create_jira_task failed: %s", e)
        raise


def _assign_sync(issue_key: str, assignee_name: str) -> str:
    jira = _get_client()
    users = jira.search_users(query=assignee_name)
    if not users:
        raise ValueError(f"No Jira user found matching '{assignee_name}'")
    jira.assign_issue(issue_key, users[0].accountId)
    return users[0].displayName


async def assign_jira_task(issue_key: str, assignee_name: str) -> str:
    """Assign an existing Jira issue to a user. Returns the matched display name."""
    try:
        return await asyncio.to_thread(_assign_sync, issue_key, assignee_name)
    except Exception as e:
        logger.error("assign_jira_task failed: %s", e)
        raise


def _delete_sync(issue_key: str) -> None:
    jira = _get_client()
    jira.delete_issue(issue_key)


async def delete_jira_task(issue_key: str) -> None:
    """Permanently delete a Jira issue by key."""
    try:
        await asyncio.to_thread(_delete_sync, issue_key)
    except Exception as e:
        logger.error("delete_jira_task failed: %s", e)
        raise


def _list_sync(assignee_name: str | None, status_filter: str | None) -> list[dict]:
    jira = _get_client()
    conditions = [f"project = {config.JIRA_PROJECT_KEY}"]

    if status_filter and status_filter.lower() == "backlog":
        # Jira backlog = issues not yet assigned to any sprint
        conditions.append("sprint is EMPTY")
        conditions.append("status != Done")
    elif status_filter:
        conditions.append(f'status = "{status_filter}"')
    else:
        conditions.append("status != Done")

    if assignee_name:
        users = jira.search_users(query=assignee_name)
        if not users:
            raise ValueError(f"No Jira user found matching '{assignee_name}'")
        conditions.append(f"assignee = '{users[0].accountId}'")
    else:
        # Resolve the authenticated user's account ID explicitly — more reliable than currentUser()
        my_account_id = jira.myself()["accountId"]
        conditions.append(f"reporter = '{my_account_id}'")

    jql = " AND ".join(conditions) + " ORDER BY created DESC"
    issues = jira.search_issues(jql, maxResults=10)
    return [
        {
            "key": issue.key,
            "summary": issue.fields.summary,
            "status": issue.fields.status.name,
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
            "priority": issue.fields.priority.name if issue.fields.priority else "Medium",
        }
        for issue in issues
    ]


async def list_jira_tasks(
    assignee_name: str | None = None,
    status_filter: str | None = None,
) -> list[dict]:
    """Return up to 10 tasks, optionally filtered by assignee name and/or status."""
    try:
        return await asyncio.to_thread(_list_sync, assignee_name, status_filter)
    except Exception as e:
        logger.error("list_jira_tasks failed: %s", e)
        raise


def _update_status_sync(issue_key: str, target_status: str) -> str:
    from rapidfuzz import fuzz, process as fz_process
    jira = _get_client()
    transitions = jira.transitions(issue_key)
    names = [t["name"] for t in transitions]
    # Exact match first (case-insensitive)
    for t in transitions:
        if t["name"].lower() == target_status.lower():
            jira.transition_issue(issue_key, t["id"])
            return t["name"]
    # Fuzzy fallback
    result = fz_process.extractOne(target_status, names, scorer=fuzz.WRatio, score_cutoff=60)
    if result:
        matched_name, _score, idx = result
        jira.transition_issue(issue_key, transitions[idx]["id"])
        return matched_name
    raise ValueError(f"No transition found for '{target_status}'. Available: {', '.join(names)}")


async def update_jira_status(issue_key: str, target_status: str) -> str:
    """Transition a Jira issue to a new status. Returns the matched transition name."""
    try:
        return await asyncio.to_thread(_update_status_sync, issue_key, target_status)
    except Exception as e:
        logger.error("update_jira_status failed: %s", e)
        raise
