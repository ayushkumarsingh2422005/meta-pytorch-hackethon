"""Shim for tools that scan ``server/graders.py`` (email-triage style layouts)."""

from env.grader import (
    grade_task_easy,
    grade_task_fraud_easy,
    grade_task_fraud_hard,
    grade_task_fraud_medium,
    grade_task_hard,
    grade_task_medium,
)

__all__ = [
    "grade_task_easy",
    "grade_task_medium",
    "grade_task_hard",
    "grade_task_fraud_easy",
    "grade_task_fraud_medium",
    "grade_task_fraud_hard",
]
