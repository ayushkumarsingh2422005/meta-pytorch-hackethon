"""Unit tests for deterministic policy, grader, and environment."""

from __future__ import annotations

import os

import pytest

from env.env import CorporateExpenseEnvironment  # noqa: E402
from env.grader import (  # noqa: E402
    episode_score,
    grade_task_fraud_easy,
    grade_task_fraud_hard,
    grade_task_fraud_medium,
    map_closed_unit_to_open_interval,
)
from env.models import CorporateExpenseAction, TrajectoryStep  # noqa: E402
from env.policy import ground_truth_for_expense  # noqa: E402
from env.policy import policy_tier  # noqa: E402
from env.tasks import HARD_EXPENSES, MEDIUM_EXPENSES, get_task_expenses  # noqa: E402


def test_fraud_task_aliases_match_short_names() -> None:
    assert get_task_expenses("fraud_easy") == get_task_expenses("easy")
    assert get_task_expenses("fraud_hard") == get_task_expenses("hard")


def test_reset_accepts_short_alias_easy() -> None:
    env = CorporateExpenseEnvironment()
    obs = env.reset(task="easy")
    assert obs.task == "easy"
    assert len(obs.pending_expenses) == len(get_task_expenses("fraud_easy"))


def test_policy_tier_normalizes_fraud_prefix() -> None:
    assert policy_tier("fraud_medium") == "medium"
    assert policy_tier("fraud_hard") == "hard"
    assert policy_tier("easy") == "easy"


def test_ground_truth_duplicate_hard() -> None:
    gt0 = ground_truth_for_expense(
        HARD_EXPENSES[0], task="hard", prior_in_episode=[]
    )
    assert gt0.decision == "approve"
    gt1 = ground_truth_for_expense(
        HARD_EXPENSES[1], task="hard", prior_in_episode=[HARD_EXPENSES[0]]
    )
    assert gt1.decision == "reject"
    assert "duplicate_claim" in gt1.fraud_flags


def test_medium_missing_receipt() -> None:
    gt = ground_truth_for_expense(
        MEDIUM_EXPENSES[2], task="medium", prior_in_episode=[]
    )
    assert gt.decision == "reject"


def test_easy_episode_high_score(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORPORATE_EXPENSE_TASK", "fraud_easy")
    env = CorporateExpenseEnvironment()
    obs = env.reset(task="fraud_easy")
    while not obs.done:
        idx = obs.current_expense_index
        cur = obs.pending_expenses[idx]
        prior = obs.pending_expenses[:idx]
        gt = ground_truth_for_expense(cur, task=obs.task, prior_in_episode=prior)
        obs = env.step(
            CorporateExpenseAction(
                decision=gt.decision,
                reason="Compliant with policy; receipt and amount are reasonable.",
            )
        )
    assert obs.episode_score is not None
    assert obs.episode_score >= 0.85


def test_openenv_yaml_parses_tasks_with_grader_field() -> None:
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[1]
    raw = yaml.safe_load((root / "openenv.yaml").read_text(encoding="utf-8"))
    tasks = raw.get("tasks") or []
    assert len(tasks) >= 3
    with_grader = [t for t in tasks if isinstance(t, dict) and t.get("grader")]
    assert len(with_grader) >= 3
    ids = [t.get("id") for t in with_grader]
    assert "fraud_easy" in ids and "fraud_medium" in ids and "fraud_hard" in ids
    for t in with_grader:
        assert ":" in str(t["grader"])


def test_root_graders_module_registry() -> None:
    import graders as root_graders

    assert len(root_graders.PRIMARY_GRADER_TASK_IDS) == 3
    for tid in root_graders.PRIMARY_GRADER_TASK_IDS:
        assert tid in root_graders.GRADERS
        s = root_graders.GRADERS[tid]()
        assert 0.0 < s < 1.0


def test_tasks_http_endpoint_lists_graders() -> None:
    from fastapi.testclient import TestClient

    from server.app import app

    client = TestClient(app)
    r = client.get("/tasks")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 3
    assert data["tasks_with_graders"] >= 3
    assert all(t.get("has_grader") for t in data["tasks"][:3])


def test_hackathon_score_strict_open_interval() -> None:
    """Phase-2: scores must be strictly inside (0, 1), not 0.0 or 1.0."""
    for fn in (grade_task_fraud_easy, grade_task_fraud_medium, grade_task_fraud_hard):
        s = fn()
        assert 0.0 < s < 1.0
        assert s != 0.0 and s != 1.0
    m = map_closed_unit_to_open_interval(0.0)
    assert m == 0.01
    assert map_closed_unit_to_open_interval(1.0) == 0.99


def test_episode_score_deterministic() -> None:
    traj = [
        TrajectoryStep(
            expense_id="x",
            decision="approve",
            reason="Within policy and receipt attached.",
            ground_truth_decision="approve",
            fraud_flags=(),
            reward=0.9,
        )
    ]
    a = episode_score(traj)
    b = episode_score(traj)
    assert a == b


def test_reset_task_kw_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORPORATE_EXPENSE_TASK", "fraud_easy")
    env = CorporateExpenseEnvironment()
    obs = env.reset(task="fraud_hard")
    assert obs.task == "fraud_hard"
    assert len(obs.pending_expenses) == len(HARD_EXPENSES)


def test_step_advances_and_done() -> None:
    os.environ["CORPORATE_EXPENSE_TASK"] = "fraud_easy"
    env = CorporateExpenseEnvironment()
    env.reset()
    n = len(env._expenses)
    for i in range(n):
        cur = env._expenses[env._cursor]
        prior = env._expenses[: env._cursor]
        gt = ground_truth_for_expense(cur, task=env._task, prior_in_episode=prior)
        obs = env.step(
            CorporateExpenseAction(decision=gt.decision, reason="test reasoning")
        )
        assert obs.current_expense_index == i + 1
        if i + 1 == n:
            assert obs.done
            assert obs.episode_score is not None
