"""
modules/jira_client.py — Jira integration: create_jira_task(intent) -> str
"""
import asyncio
import logging

from jira import JIRA

import config
from modules.models import IntentResult, SearchFilters

logger = logging.getLogger(__name__)


def _get_client() -> JIRA:
    return JIRA(
        server=config.JIRA_URL,
        basic_auth=(config.JIRA_EMAIL, config.JIRA_API_TOKEN),
    )


def _create_sync(intent: IntentResult) -> str:
    """Synchronous Jira issue creation (run via asyncio.to_thread)."""
    jira = _get_client()
    project_key = intent.project or config.JIRA_PROJECT_KEY

    fields: dict = {
        "project": {"key": project_key},
        "summary": intent.summary,
        "issuetype": {"name": intent.issue_type},
        "priority": {"name": intent.priority or "Medium"},
    }
    if intent.description:
        fields["description"] = intent.description
    if intent.story_points is not None:
        fields["story_points"] = intent.story_points

    issue = jira.create_issue(fields=fields)

    if intent.assignee_name:
        try:
            users = jira.search_users(query=intent.assignee_name)
            if users:
                jira.assign_issue(issue, users[0].accountId)
        except Exception as e:
            logger.warning("Could not assign '%s': %s", intent.assignee_name, e)

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


def _search_sync(filters: SearchFilters | None, project_key: str) -> list[dict]:
    jira = _get_client()
    conditions = [f"project = {project_key}"]

    if filters:
        if filters.status and filters.status.lower() == "backlog":
            conditions.append("sprint is EMPTY")
            conditions.append("status != Done")
        elif filters.status:
            conditions.append(f'status = "{filters.status}"')
        else:
            conditions.append("status != Done")

        if filters.assignee:
            if filters.assignee.lower() == "me":
                my_account_id = jira.myself()["accountId"]
                conditions.append(f"assignee = '{my_account_id}'")
            else:
                users = jira.search_users(query=filters.assignee)
                if not users:
                    raise ValueError(f"No Jira user found matching '{filters.assignee}'")
                conditions.append(f"assignee = '{users[0].accountId}'")

        if filters.priority:
            conditions.append(f'priority = "{filters.priority}"')

        if filters.issue_type:
            conditions.append(f'issuetype = "{filters.issue_type}"')

        if filters.created_after:
            conditions.append(f'created >= "{filters.created_after}"')

        if filters.due_before:
            conditions.append(f'due <= "{filters.due_before}"')
    else:
        conditions.append("status != Done")
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


async def search_jira_tasks(
    filters: SearchFilters | None = None,
    project_key: str | None = None,
) -> list[dict]:
    """Return up to 10 tasks matching the given filters."""
    try:
        return await asyncio.to_thread(_search_sync, filters, project_key or config.JIRA_PROJECT_KEY)
    except Exception as e:
        logger.error("search_jira_tasks failed: %s", e)
        raise


def _update_status_sync(issue_key: str, target_status: str) -> str:
    from rapidfuzz import fuzz, process as fz_process
    jira = _get_client()
    transitions = jira.transitions(issue_key)
    names = [t["name"] for t in transitions]
    for t in transitions:
        if t["name"].lower() == target_status.lower():
            jira.transition_issue(issue_key, t["id"])
            return t["name"]
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


def _add_comment_sync(issue_key: str, comment_text: str) -> None:
    jira = _get_client()
    jira.add_comment(issue_key, comment_text)


async def add_jira_comment(issue_key: str, comment_text: str) -> None:
    """Add a comment to an existing Jira issue."""
    try:
        await asyncio.to_thread(_add_comment_sync, issue_key, comment_text)
    except Exception as e:
        logger.error("add_jira_comment failed: %s", e)
        raise


def _change_priority_sync(issue_key: str, priority: str) -> None:
    jira = _get_client()
    jira.issue(issue_key).update(fields={"priority": {"name": priority}})


async def change_jira_priority(issue_key: str, priority: str) -> None:
    """Update the priority of an existing Jira issue."""
    try:
        await asyncio.to_thread(_change_priority_sync, issue_key, priority)
    except Exception as e:
        logger.error("change_jira_priority failed: %s", e)
        raise


def _update_task_sync(intent: IntentResult) -> None:
    jira = _get_client()
    fields: dict = {}
    if intent.summary:
        fields["summary"] = intent.summary
    if intent.description:
        fields["description"] = intent.description
    if intent.priority is not None:
        fields["priority"] = {"name": intent.priority}
    if fields:
        jira.issue(intent.issue_key).update(fields=fields)


async def update_jira_task(intent: IntentResult) -> None:
    """Update fields on an existing Jira issue."""
    try:
        await asyncio.to_thread(_update_task_sync, intent)
    except Exception as e:
        logger.error("update_jira_task failed: %s", e)
        raise
