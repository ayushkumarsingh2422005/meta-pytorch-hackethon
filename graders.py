"""
Root-level grader module for hackathon / Phase-2 validators.

Many pipelines look for ``graders.py`` at the repository root and/or import
``graders:grade_task_*`` entrypoints declared in ``openenv.yaml``.

Implementation lives in ``env.grader``; this module re-exports stable symbols.
"""

from __future__ import annotations

from typing import Callable

from env.grader import (
    TASK_GRADER_EXPORTS,
    episode_score,
    grade_task_easy,
    grade_task_fraud_easy,
    grade_task_fraud_hard,
    grade_task_fraud_medium,
    grade_task_hard,
    grade_task_medium,
    map_closed_unit_to_open_interval,
    oracle_trajectory_for_task,
)

# Callable registry (validators may introspect dict[str, Callable])
GRADERS: dict[str, Callable[[], float]] = {
    "easy": grade_task_easy,
    "medium": grade_task_medium,
    "hard": grade_task_hard,
    "fraud_easy": grade_task_fraud_easy,
    "fraud_medium": grade_task_fraud_medium,
    "fraud_hard": grade_task_fraud_hard,
}

# String entrypoints matching openenv.yaml (module:function)
GRADER_ENTRYPOINTS: dict[str, str] = {
    "easy": "graders:grade_task_easy",
    "medium": "graders:grade_task_medium",
    "hard": "graders:grade_task_hard",
    "fraud_easy": "graders:grade_task_fraud_easy",
    "fraud_medium": "graders:grade_task_fraud_medium",
    "fraud_hard": "graders:grade_task_fraud_hard",
}

# Canonical public task IDs (competition / openenv.yaml)
PRIMARY_GRADER_TASK_IDS = ("fraud_easy", "fraud_medium", "fraud_hard")

__all__ = [
    "episode_score",
    "grade_task_easy",
    "grade_task_fraud_easy",
    "grade_task_fraud_hard",
    "grade_task_fraud_medium",
    "grade_task_hard",
    "grade_task_medium",
    "GRADERS",
    "GRADER_ENTRYPOINTS",
    "map_closed_unit_to_open_interval",
    "oracle_trajectory_for_task",
    "PRIMARY_GRADER_TASK_IDS",
    "TASK_GRADER_EXPORTS",
]
