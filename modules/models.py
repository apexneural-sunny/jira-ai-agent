"""
modules/models.py — Pydantic v2 models for structured data
"""
from typing import Optional
from pydantic import BaseModel


class IntentResult(BaseModel):
    action: str = "create"          # create | assign | delete | list | update_status
    title: Optional[str] = None     # required for create
    issue_key: Optional[str] = None # required for assign / delete / update_status
    status: Optional[str] = None    # required for update_status (e.g. "In Progress", "Done")
    description: Optional[str] = None
    assignee: Optional[str] = None      # name filter for list; person for assign/create
    status_filter: Optional[str] = None # status filter for list (e.g. "Backlog", "In Progress")
    priority: Optional[str] = "Medium"
    story_points: Optional[int] = None
    issue_type: str = "Task"
