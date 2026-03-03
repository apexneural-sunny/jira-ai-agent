"""
modules/models.py — Pydantic v2 models for structured data
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SearchFilters(BaseModel):
    assignee: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    issue_type: Optional[str] = None
    project: Optional[str] = None
    created_after: Optional[str] = None
    due_before: Optional[str] = None


class BulkOperationFilters(BaseModel):
    assignee: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    created_after: Optional[str] = None


class AutomationRule(BaseModel):
    trigger: Optional[str] = None
    action: Optional[str] = None
    conditions: Optional[str] = None


class IntentResult(BaseModel):
    # Core
    action: str = "create_task"
    summary: Optional[str] = None           # task title (required for create_task)
    description: Optional[str] = None
    project: Optional[str] = None           # project key, null = use default
    issue_type: str = "Task"
    priority: Optional[str] = None
    story_points: Optional[int] = None

    # References
    assignee_name: Optional[str] = None     # person name for assign/create
    issue_key: Optional[str] = None         # e.g. SCRUM-42

    # Action-specific
    comment_text: Optional[str] = None      # for add_comment
    status_transition: Optional[str] = None # for change_status (e.g. "In Progress")

    # Clarification
    needs_clarification: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    clarification_question: Optional[str] = None

    @field_validator("missing_fields", mode="before")
    @classmethod
    def coerce_missing_fields(cls, v: object) -> list:
        return v if isinstance(v, list) else []

    # Search
    search_filters: Optional[SearchFilters] = None

    # Analytics
    analytics_type: Optional[str] = None   # summary | velocity | trends | workload

    # Bulk operations
    bulk_operation_filters: Optional[BulkOperationFilters] = None
    bulk_operation_action: Optional[str] = None  # update_status | update_priority | assign_to | add_comment

    # Notifications
    notification_type: Optional[str] = None    # issue_update | new_issue | status_change | mention
    notification_target: Optional[str] = None  # issue_key | project | assignee

    # Automation
    automation_rule: Optional[AutomationRule] = None
