"""
Deterministic step rewards and episode scores.

Hackathon Phase-2 expects episode scores strictly inside (0, 1), not 0.0 or 1.0.
We compute in [0, 1] then map linearly to [SCORE_OPEN_MIN, SCORE_OPEN_MAX].
"""

from __future__ import annotations

import re
from typing import Iterable, Literal, cast

from env.models import StepRewardBreakdown, TrajectoryStep
from env.policy import GroundTruth, ground_truth_for_expense

# Strict open interval (validator: not 0.0, not 1.0)
SCORE_OPEN_MIN = 0.01
SCORE_OPEN_MAX = 0.99

_FRAUD_KEYWORDS = (
    "duplicate",
    "receipt",
    "missing",
    "fraud",
    "suspicious",
    "anomal",
    "policy",
    "violation",
    "high",
    "amount",
    "travel",
    "equipment",
)


def map_closed_unit_to_open_interval(closed_01: float) -> float:
    """Map a value in [0, 1] to [SCORE_OPEN_MIN, SCORE_OPEN_MAX] (strict subset of (0,1))."""
    u = max(0.0, min(1.0, float(closed_01)))
    return round(SCORE_OPEN_MIN + u * (SCORE_OPEN_MAX - SCORE_OPEN_MIN), 6)


def _reasoning_quality(reason: str, flags: tuple[str, ...]) -> float:
    """0..0.2 based on length and keyword relevance."""
    r = reason.strip()
    if len(r) < 12:
        return 0.0
    score = 0.0
    if len(r) >= 40:
        score += 0.1
    else:
        score += 0.05
    low = r.lower()
    if flags:
        if any(kw in low for kw in _FRAUD_KEYWORDS):
            score += 0.1
    else:
        if any(kw in low for kw in ("policy", "receipt", "valid", "appropriate", "within")):
            score += 0.1
        else:
            score += 0.05
    return min(0.2, score)


def _fraud_component(
    decision: str,
    gt: GroundTruth,
    reason: str,
) -> float:
    """0..0.2 fraud-detection credit."""
    if not gt.fraud_flags:
        return 0.2
    low = reason.lower()
    mentioned = any(kw in low for kw in _FRAUD_KEYWORDS)
    correct_reject = decision == "reject" and gt.decision == "reject"
    if correct_reject and (mentioned or "duplicate" in gt.fraud_flags):
        return 0.2
    if correct_reject:
        return 0.15
    if mentioned:
        return 0.08
    return 0.0


def compute_step_reward(
    *,
    decision: str,
    reason: str,
    gt: GroundTruth,
) -> tuple[float, StepRewardBreakdown]:
    """Return step reward in the open interval (SCORE_OPEN_MIN, SCORE_OPEN_MAX)."""
    breakdown = StepRewardBreakdown()
    total = 0.0

    correct = decision == gt.decision
    if correct:
        total += 0.5
        breakdown.correct = 0.5
    else:
        total -= 0.3
        breakdown.incorrect_penalty = -0.3

    rq = _reasoning_quality(reason, gt.fraud_flags)
    total += rq
    breakdown.reasoning = rq

    fc = _fraud_component(decision, gt, reason)
    total += fc
    breakdown.fraud = fc

    risky = (
        decision == "approve"
        and gt.decision == "reject"
        and bool(gt.fraud_flags)
    )
    if risky:
        total -= 0.2
        breakdown.risky_approval_penalty = -0.2

    breakdown.raw_total = total
    closed = max(0.0, min(1.0, total))
    mapped = map_closed_unit_to_open_interval(closed)
    return mapped, breakdown


def _episode_score_closed_unit(trajectory: Iterable[TrajectoryStep]) -> float:
    """Aggregate in [0, 1] before open-interval mapping."""
    steps = list(trajectory)
    if not steps:
        return 0.0

    n = len(steps)
    correct = sum(
        1 for s in steps if s.decision == s.ground_truth_decision
    ) / n

    reasoning = []
    for s in steps:
        reasoning.append(_reasoning_quality(s.reason, s.fraud_flags))
    reasoning_mean = sum(reasoning) / n / 0.2

    fraud_steps = [s for s in steps if s.fraud_flags]
    if not fraud_steps:
        fraud_score = 1.0
    else:
        hits = 0.0
        for s in fraud_steps:
            low = s.reason.lower()
            ok = s.decision == "reject" and s.ground_truth_decision == "reject"
            mentioned = any(kw in low for kw in _FRAUD_KEYWORDS)
            if ok and mentioned:
                hits += 1.0
            elif ok:
                hits += 0.7
        fraud_score = hits / len(fraud_steps)

    score = 0.45 * correct + 0.30 * min(1.0, reasoning_mean) + 0.25 * fraud_score
    return max(0.0, min(1.0, round(score, 6)))


def episode_score(trajectory: Iterable[TrajectoryStep]) -> float:
    """
    Deterministic aggregate strictly inside (0, 1).

    Empty trajectory maps to SCORE_OPEN_MIN so the value is never exactly 0.0.
    """
    closed = _episode_score_closed_unit(trajectory)
    return map_closed_unit_to_open_interval(closed)


def oracle_trajectory_for_task(task: str) -> list[TrajectoryStep]:
    """Reference transcript: always matches ground-truth decisions with rich reasons."""
    from env.tasks import get_task_expenses

    expenses = get_task_expenses(task)
    traj: list[TrajectoryStep] = []
    reason = (
        "Oracle: aligns with policy; notes receipt, duplicate, or fraud cues where relevant."
    )
    for idx, cur in enumerate(expenses):
        prior = expenses[:idx]
        gt = ground_truth_for_expense(cur, task=task, prior_in_episode=prior)
        traj.append(
            TrajectoryStep(
                expense_id=cur.id,
                decision=cast(Literal["approve", "reject"], gt.decision),
                reason=reason,
                ground_truth_decision=cast(Literal["approve", "reject"], gt.decision),
                fraud_flags=gt.fraud_flags,
                reward=0.0,
            )
        )
    return traj


def grade_task_easy() -> float:
    """Grader hook for task ``easy`` (validator / openenv.yaml)."""
    return episode_score(oracle_trajectory_for_task("easy"))


def grade_task_medium() -> float:
    """Grader hook for task ``medium``."""
    return episode_score(oracle_trajectory_for_task("medium"))


def grade_task_hard() -> float:
    """Grader hook for task ``hard``."""
    return episode_score(oracle_trajectory_for_task("hard"))


def grade_task_fraud_easy() -> float:
    return episode_score(oracle_trajectory_for_task("fraud_easy"))


def grade_task_fraud_medium() -> float:
    return episode_score(oracle_trajectory_for_task("fraud_medium"))


def grade_task_fraud_hard() -> float:
    return episode_score(oracle_trajectory_for_task("fraud_hard"))


# Registry for tools that introspect the module
TASK_GRADER_EXPORTS: dict[str, str] = {
    "easy": "grade_task_easy",
    "medium": "grade_task_medium",
    "hard": "grade_task_hard",
    "fraud_easy": "grade_task_fraud_easy",
    "fraud_medium": "grade_task_fraud_medium",
    "fraud_hard": "grade_task_fraud_hard",
}
