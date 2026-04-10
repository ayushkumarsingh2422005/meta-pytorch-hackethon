# Copyright (c) Contributors to the corporate expense OpenEnv environment.
"""FastAPI application exposing the corporate expense approval environment."""

from __future__ import annotations

import json
from pathlib import Path

from openenv.core.env_server import create_app

from env.env import CorporateExpenseEnvironment
from models import CorporateExpenseAction, CorporateExpenseObservation

app = create_app(
    CorporateExpenseEnvironment,
    CorporateExpenseAction,
    CorporateExpenseObservation,
    env_name="corporate_expense_approval",
)

# Canonical task IDs: fraud_* (matches openenv.yaml / task_manifest.json)
_TASKS_WITH_GRADERS = [
    {
        "id": "fraud_easy",
        "name": "Routine valid expenses",
        "difficulty": "easy",
        "grader": "graders:grade_task_fraud_easy",
        "has_grader": True,
    },
    {
        "id": "fraud_medium",
        "name": "Receipt policy stress",
        "difficulty": "medium",
        "grader": "graders:grade_task_fraud_medium",
        "has_grader": True,
    },
    {
        "id": "fraud_hard",
        "name": "Fraud and anomaly patterns",
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
        "tasks_with_graders": [t for t in _TASKS_WITH_GRADERS if t.get("has_grader")],
    }


def _task_manifest_path() -> Path:
    here = Path(__file__).resolve().parent.parent
    return here / "task_manifest.json"


@app.get("/task-manifest")
def http_task_manifest() -> dict:
    """Same data as root ``task_manifest.json`` (JSON-friendly Phase-2 discovery)."""
    p = _task_manifest_path()
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "tasks_with_graders": _TASKS_WITH_GRADERS,
        "error": "task_manifest.json not found on server",
    }


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
