from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.learning_service import LearningService
from agent.review_service import ReviewRateLimited, ReviewService
from storage.learning_repository import LearningRepository


NOW = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)


@pytest.fixture()
def learning(app_container):
    repository = LearningRepository(app_container.database, now=lambda: NOW)
    repository.publish_fixture(
        content_id="content-kubernetes", content_version="v1", roadmap_id="roadmap-a",
        milestone_key="containers", title="Kubernetes fundamentals", objective="Deploy safely",
        estimated_minutes=25,
        steps=[("read", "reading", "Read"), ("lab", "lab", "Practice"), ("review", "review", "Review")],
        questions=[
            ("q1", "One?", {"a": "A", "b": "B"}, "a", "A is correct"),
            ("q2", "Two?", {"a": "A", "b": "B"}, "a", "A is correct"),
            ("q3", "Three?", {"a": "A", "b": "B"}, "a", "A is correct"),
            ("q4", "Four?", {"a": "A", "b": "B"}, "a", "A is correct"),
        ],
        lab_reference_versions=["lab-kubernetes@v1"],
    )
    return repository, LearningService(repository), ReviewService(repository)


def test_start_resume_cursor_and_atomic_pass_completion(learning) -> None:
    repository, sessions, reviews = learning
    first = sessions.start("employee-a", "content-kubernetes", "v1")
    resumed = sessions.start("employee-a", "content-kubernetes", "v1")
    assert resumed["id"] == first["id"]
    assert first["content_version"] == "v1"
    sessions.complete_step("employee-a", first["id"], "read")
    assert sessions.get("employee-a", first["id"])["current_step_ordinal"] == 1
    attempt = reviews.start_attempt("employee-a", first["id"])
    assert [question["id"] for question in attempt["questions"]] == ["q1", "q2", "q3", "q4"]
    for question_id in ("q1", "q2", "q3", "q4"):
        feedback = reviews.answer("employee-a", attempt["id"], question_id, "a")
        assert set(feedback) == {"question_id", "submitted_answer_key", "correct", "explanation", "answered_at"}
    result = reviews.submit("employee-a", attempt["id"])
    assert result["score_percent"] == 100
    assert result["passed"] is True
    assert sessions.get("employee-a", first["id"])["status"] == "completed"
    assert repository.milestone_completion_count("employee-a", "roadmap-a", "containers") == 1


def test_failed_attempt_requires_fresh_full_attempt_without_copied_answers(learning) -> None:
    _, sessions, reviews = learning
    session = sessions.start("employee-b", "content-kubernetes", "v1")
    attempt = reviews.start_attempt("employee-b", session["id"])
    for question_id, answer in (("q1", "a"), ("q2", "a"), ("q3", "b"), ("q4", "b")):
        reviews.answer("employee-b", attempt["id"], question_id, answer)
    result = reviews.submit("employee-b", attempt["id"])
    assert result["score_percent"] == 50
    assert result["passed"] is False
    assert result["next_action"]["kind"] == "retry_material"
    assert result["missed_question_ids"] == ["q3", "q4"]
    retry = reviews.start_attempt("employee-b", session["id"])
    assert retry["attempt_number"] == 2
    assert retry["answers"] == []
    assert [item["id"] for item in retry["questions"]] == ["q1", "q2", "q3", "q4"]


def test_sixth_new_attempt_in_rolling_hour_is_rate_limited(learning) -> None:
    repository, sessions, _ = learning
    session = sessions.start("employee-c", "content-kubernetes", "v1")
    reviews = ReviewService(repository)
    for number in range(5):
        attempt = reviews.start_attempt("employee-c", session["id"])
        for question in attempt["questions"]:
            reviews.answer("employee-c", attempt["id"], question["id"], "b")
        reviews.submit("employee-c", attempt["id"])
    with pytest.raises(ReviewRateLimited) as raised:
        reviews.start_attempt("employee-c", session["id"])
    assert raised.value.retry_after_seconds == 900


def test_mutations_are_idempotent_and_survive_repository_restart(learning, app_container) -> None:
    repository, sessions, reviews = learning
    started = sessions.start("employee-d", "content-kubernetes", "v1")
    restarted = LearningRepository(app_container.database, now=lambda: NOW)
    resumed = LearningService(restarted).start("employee-d", "content-kubernetes", "v1")
    assert resumed["id"] == started["id"]
    attempt = reviews.start_attempt("employee-d", started["id"])
    first = reviews.answer("employee-d", attempt["id"], "q1", "a")
    replay = reviews.answer("employee-d", attempt["id"], "q1", "a")
    assert replay == first


def test_attempt_history_is_immutable_and_first_pass_is_permanent(learning) -> None:
    repository, sessions, reviews = learning
    learning_session = sessions.start("employee-e", "content-kubernetes", "v1")
    attempt = reviews.start_attempt("employee-e", learning_session["id"])
    for question in attempt["questions"]:
        reviews.answer("employee-e", attempt["id"], question["id"], "a")
    submitted = reviews.submit("employee-e", attempt["id"])
    assert reviews.submit("employee-e", attempt["id"]) == submitted
    with pytest.raises(ValueError, match="FINALIZED"):
        reviews.answer("employee-e", attempt["id"], "q1", "a")
    with pytest.raises(ValueError, match="COMPLETED"):
        reviews.start_attempt("employee-e", learning_session["id"])
    restored = repository.list_attempts("employee-e", learning_session["id"])
    assert restored[0]["status"] == "submitted"
    assert restored[0]["score_percent"] == 100
    assert len(restored[0]["answers"]) == 4


def test_lab_state_reload_preserves_pin_and_never_completes_a_step(learning) -> None:
    repository, sessions, _ = learning
    learning_session = sessions.start("employee-f", "content-kubernetes", "v1")
    before = sessions.get("employee-f", learning_session["id"])
    state = repository.reload_lab_state("employee-f", learning_session["id"], "lab-kubernetes@v1", "unavailable", "paid")
    after = sessions.get("employee-f", learning_session["id"])
    assert state["availability_state"] == "unavailable"
    assert before["steps"] == after["steps"]
    assert after["lab_reference_versions"] == ["lab-kubernetes@v1"]


def test_attempt_limit_is_rolling_not_lifetime(learning) -> None:
    repository, sessions, reviews = learning
    learning_session = sessions.start("employee-g", "content-kubernetes", "v1")
    for _ in range(5):
        attempt = reviews.start_attempt("employee-g", learning_session["id"])
        for question in attempt["questions"]:
            reviews.answer("employee-g", attempt["id"], question["id"], "b")
        reviews.submit("employee-g", attempt["id"])
    repository.now = lambda: NOW + timedelta(minutes=61)
    sixth = reviews.start_attempt("employee-g", learning_session["id"])
    assert sixth["attempt_number"] == 6


def test_security_retirement_blocks_review_immediately_and_mixed_questions_are_denied(learning) -> None:
    repository, sessions, reviews = learning
    learning_session = sessions.start("employee-h", "content-kubernetes", "v1")
    attempt = reviews.start_attempt("employee-h", learning_session["id"])
    with pytest.raises(ValueError):
        reviews.answer("employee-h", attempt["id"], "question-from-v2", "a")
    repository.retire_content("content-kubernetes", "v1", security_critical=True, resume_until=NOW + timedelta(days=30))
    with pytest.raises(ValueError, match="SECURITY_RETIRED"):
        reviews.answer("employee-h", attempt["id"], "q1", "a")


def test_lab_reports_are_append_only_and_required_clock_segments_persist(learning) -> None:
    repository, sessions, _ = learning
    learning_session = sessions.start("employee-i", "content-kubernetes", "v1")
    sessions.reload_lab("employee-i", learning_session["id"], "lab-kubernetes@v1", "active", "free")
    first = sessions.report_lab("employee-i", learning_session["id"], "lab-kubernetes@v1", "unavailable")
    second = sessions.report_lab("employee-i", learning_session["id"], "lab-kubernetes@v1", "cost_mismatch")
    assert first["id"] != second["id"]
    assert repository.get_lab_state("employee-i", learning_session["id"], "lab-kubernetes@v1")["reported_at"] is not None
    segment = sessions.start_required_clock("employee-i", learning_session["id"], NOW)
    assert sessions.start_required_clock("employee-i", learning_session["id"], NOW) == segment
    ended = sessions.pause_required_clock("employee-i", learning_session["id"], NOW + timedelta(seconds=30), "before_external_lab")
    assert ended["duration_ms"] == 30_000


def test_repository_restores_labeled_history_and_supplies_next_action_candidates(learning) -> None:
    repository, sessions, reviews = learning
    learning_session = sessions.start("employee-j", "content-kubernetes", "v1")
    attempt = reviews.start_attempt("employee-j", learning_session["id"])
    for question in attempt["questions"]:
        reviews.answer("employee-j", attempt["id"], question["id"], "b")
    reviews.submit("employee-j", attempt["id"])
    history = repository.list_attempts("employee-j", learning_session["id"])
    assert history[0]["latest"] is history[0]["highest"] is True
    candidates = repository.learning_candidates("employee-j", "roadmap-a")
    assert len(candidates) == 1 and candidates[0].action_type == "retry_material"
