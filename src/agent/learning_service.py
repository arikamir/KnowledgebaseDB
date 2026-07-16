"""Pinned learning-session lifecycle rules."""

from __future__ import annotations

from datetime import datetime

from storage.learning_repository import LearningRepository


def content_resume_decision(*, retired_at: datetime | None, resume_until: datetime | None, security_critical: bool, now: datetime) -> str:
    if retired_at is None:
        return "active"
    if security_critical:
        return "security_blocked"
    return "resume" if resume_until is not None and now <= resume_until else "retired"


def replacement_is_copy_eligible(original: dict, replacement: dict) -> bool:
    return original.get("objective") == replacement.get("objective") and original.get("step_ids") == replacement.get("step_ids")


class LearningService:
    def __init__(self, repository: LearningRepository) -> None:
        self.repository = repository

    def start(self, employee_id: str, content_id: str, version: str) -> dict:
        content = self.repository.content(content_id, version)
        if content is None:
            raise ValueError("LEARNING_CONTENT_NOT_FOUND")
        decision = content_resume_decision(retired_at=content.retired_at, resume_until=content.resume_until, security_critical=content.security_critical_retirement, now=self.repository.now())
        if decision == "security_blocked":
            raise ValueError("CONTENT_VERSION_SECURITY_RETIRED")
        if decision == "retired":
            raise ValueError("CONTENT_VERSION_RETIRED")
        return self.repository.start_session(employee_id, content_id, version)

    def get(self, employee_id: str, session_id: str) -> dict:
        result = self.repository.get_session(employee_id, session_id)
        if result is None:
            raise ValueError("LEARNING_SESSION_NOT_FOUND")
        return result

    def complete_step(self, employee_id: str, session_id: str, step_id: str) -> dict:
        return self.repository.complete_step(employee_id, session_id, step_id)
