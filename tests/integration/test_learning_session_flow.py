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
