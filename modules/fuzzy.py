"""
modules/fuzzy.py — Fuzzy name matching: find_assignee(name, users) -> dict | None
"""
from typing import Optional

from rapidfuzz import fuzz, process


def find_assignee(name: str, users: list[dict]) -> Optional[dict]:
    """Fuzzy-match a spoken name against a list of Jira user dicts.

    Each dict must have a 'displayName' key.
    Returns the best match if score >= 70, otherwise None.
    """
    if not name or not users:
        return None
    display_names = [u["displayName"] for u in users]
    result = process.extractOne(name, display_names, scorer=fuzz.WRatio, score_cutoff=70)
    if result is None:
        return None
    _matched_name, _score, index = result
    return users[index]
