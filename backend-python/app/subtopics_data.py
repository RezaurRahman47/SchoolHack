"""Subtopics data module.

Curriculum units and subtopics are structured directly in HTML (chemie.html).
No hardcoded flashcards, true/false questions, or cached practice data.
"""
from __future__ import annotations

SUBTOPIC_DATA: dict[str, dict] = {}


def get_subtopic_data(skill: str) -> dict:
    """Return subtopic data dictionary for a skill (empty by default)."""
    return SUBTOPIC_DATA.get(skill, {})
