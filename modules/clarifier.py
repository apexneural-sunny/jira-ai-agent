"""
modules/clarifier.py — Clarification prompts: get_clarification_question(field) -> str
"""

_QUESTIONS: dict[str, str] = {
    "title": "What should the task title be?",
    "assignee": "Who should this task be assigned to?",
    "priority": "What priority? (Low / Medium / High / Critical)",
    "story_points": "How many story points for this task?",
    "description": "Can you add more detail or a description?",
    "issue_type": "What type of issue? (Task / Bug / Story / Epic)",
}


def get_clarification_question(field: str) -> str:
    return _QUESTIONS.get(field, f"Can you clarify the {field}?")
