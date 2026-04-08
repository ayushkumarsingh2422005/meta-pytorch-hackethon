# Copyright (c) Contributors to the corporate expense OpenEnv environment.
"""FastAPI application exposing the corporate expense approval environment."""

from __future__ import annotations

from openenv.core.env_server import create_app

from env.env import CorporateExpenseEnvironment
from models import CorporateExpenseAction, CorporateExpenseObservation

app = create_app(
    CorporateExpenseEnvironment,
    CorporateExpenseAction,
    CorporateExpenseObservation,
    env_name="corporate_expense_approval",
)

# --- Hackathon / validator helpers: explicit task + grader discovery over HTTP ---
_TASKS_WITH_GRADERS = [
    {
        "id": "easy",
        "name": "Routine valid expenses",
        "difficulty": "easy",
        "grader": "graders:grade_task_easy",
        "has_grader": True,
    },
    {
        "id": "medium",
        "name": "Receipt policy stress",
        "difficulty": "medium",
        "grader": "graders:grade_task_medium",
        "has_grader": True,
    },
    {
        "id": "hard",
        "name": "Fraud and anomaly patterns",
        "difficulty": "hard",
        "grader": "graders:grade_task_hard",
        "has_grader": True,
    },
    {
        "id": "fraud_easy",
        "difficulty": "easy",
        "grader": "graders:grade_task_fraud_easy",
        "has_grader": True,
    },
    {
        "id": "fraud_medium",
        "difficulty": "medium",
        "grader": "graders:grade_task_fraud_medium",
        "has_grader": True,
    },
    {
        "id": "fraud_hard",
        "difficulty": "hard",
        "grader": "graders:grade_task_fraud_hard",
        "has_grader": True,
    },
]


@app.get("/tasks")
def list_tasks_with_graders() -> dict:
    """List tasks that have associated grader entrypoints (Phase-2 style check)."""
    return {
        "tasks": _TASKS_WITH_GRADERS,
        "count": len(_TASKS_WITH_GRADERS),
        "tasks_with_graders": sum(1 for t in _TASKS_WITH_GRADERS if t.get("has_grader")),
    }


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
