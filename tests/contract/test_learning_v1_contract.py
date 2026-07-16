from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent.learning_service import content_resume_decision, replacement_is_copy_eligible
from agent.review_service import label_attempt_history
from agent.next_action import LearningCandidate, MilestoneCandidate, select_next_action


NOW = datetime(2026, 7, 16, tzinfo=timezone.utc)


def test_normal_and_security_retirement_have_exact_resume_rules() -> None:
    assert content_resume_decision(retired_at=None, resume_until=None, security_critical=False, now=NOW) == "active"
    assert content_resume_decision(retired_at=NOW, resume_until=NOW + timedelta(days=30), security_critical=False, now=NOW) == "resume"
    assert content_resume_decision(retired_at=NOW, resume_until=NOW - timedelta(seconds=1), security_critical=False, now=NOW) == "retired"
    assert content_resume_decision(retired_at=NOW, resume_until=NOW + timedelta(days=30), security_critical=True, now=NOW) == "security_blocked"


def test_replacement_copy_requires_identical_stable_objective_and_steps() -> None:
    original = {"objective": "Deploy safely", "step_ids": ["read", "lab", "review"]}
    assert replacement_is_copy_eligible(original, dict(original)) is True
    assert replacement_is_copy_eligible(original, {**original, "step_ids": ["read", "review"]}) is False
    assert replacement_is_copy_eligible(original, {**original, "objective": "Operate safely"}) is False


def test_attempt_history_is_chronological_with_latest_and_highest_labels() -> None:
    history = label_attempt_history([
        {"id": "second", "attempt_number": 2, "score_percent": 75.0},
        {"id": "first", "attempt_number": 1, "score_percent": 50.0},
        {"id": "third", "attempt_number": 3, "score_percent": 100.0},
    ])
    assert [item["id"] for item in history] == ["first", "second", "third"]
    assert history[-1]["latest"] is True
    assert history[-1]["highest"] is True
    assert all(item["latest"] is False for item in history[:-1])


def test_next_action_prioritizes_retry_then_resume_with_stable_ties() -> None:
    milestones = [MilestoneCandidate("roadmap", "m1", 0, "Continue")]
    learning = [
        LearningCandidate("resume_session", "roadmap", "m1", "Resume", 0, "2026-01-01", "b"),
        LearningCandidate("retry_material", "roadmap", "m1", "Retry later", 1, "2026-01-01", "c"),
        LearningCandidate("retry_material", "roadmap", "m1", "Retry first", 0, "2026-01-01", "a"),
    ]
    assert select_next_action("roadmap", milestones, learning).title == "Retry first"
    assert select_next_action("roadmap", milestones).action_type == "continue_milestone"
