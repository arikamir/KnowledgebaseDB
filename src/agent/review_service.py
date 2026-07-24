"""Immutable review scoring and retry rules."""

from __future__ import annotations

from storage.learning_repository import LearningRepository


class ReviewRateLimited(RuntimeError):
    def __init__(self) -> None:
        super().__init__("REVIEW_RETRY_RATE_LIMITED")
        self.retry_after_seconds = 900


def label_attempt_history(attempts: list[dict]) -> list[dict]:
    ordered = sorted(attempts, key=lambda item: (item["attempt_number"], item["id"]))
    highest = max((item.get("score_percent") for item in ordered if item.get("score_percent") is not None), default=None)
    return [{**item, "latest": index == len(ordered) - 1, "highest": highest is not None and item.get("score_percent") == highest} for index, item in enumerate(ordered)]


class ReviewService:
    def __init__(self, repository: LearningRepository) -> None:
        self.repository = repository

    def start_attempt(self, employee_id: str, session_id: str) -> dict:
        try:
            return self.repository.start_attempt(employee_id, session_id)
        except OverflowError as error:
            raise ReviewRateLimited() from error

    def answer(self, employee_id: str, attempt_id: str, question_id: str, answer_key: str) -> dict:
        return self.repository.answer(employee_id, attempt_id, question_id, answer_key)

    def submit(self, employee_id: str, attempt_id: str) -> dict:
        return self.repository.submit_attempt(employee_id, attempt_id)
