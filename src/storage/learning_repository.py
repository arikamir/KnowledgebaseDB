"""Owner-scoped persistence for pinned learning and immutable reviews."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from sqlalchemy import func, select

from storage.database import DatabaseManager, utcnow
from storage.learning_models import (
    EmployeeLearningSessionRecord, LearningContentRecord, LearningMilestoneCompletionRecord,
    LearningLabReportRecord, LearningLabStateRecord, LearningStepRecord, RequiredClockSegmentRecord,
    ReviewAnswerRecord, ReviewAttemptRecord, ReviewQuestionRecord, StepProgressRecord,
)


@dataclass(frozen=True, slots=True)
class PersistedLearningCandidate:
    action_type: str
    roadmap_id: str
    milestone_key: str
    title: str
    ordinal: int
    unresolved_at: str
    stable_id: str


class LearningRepository:
    def __init__(self, database: DatabaseManager, now: Callable[[], datetime] = utcnow) -> None:
        self.database = database
        self.now = now

    def publish_fixture(self, *, content_id: str, content_version: str, roadmap_id: str, milestone_key: str, title: str, objective: str, estimated_minutes: int, steps, questions, lab_reference_versions=()) -> None:
        if not 3 <= len(questions) <= 5:
            raise ValueError("published content requires 3-5 questions")
        with self.database.session() as session:
            session.add(LearningContentRecord(id=content_id, content_version=content_version, roadmap_id=roadmap_id, milestone_key=milestone_key, title=title, objective=objective, estimated_minutes=estimated_minutes, status="published", body_snapshot={"step_ids": [item[0] for item in steps]}, question_version=content_version, lab_reference_versions=list(lab_reference_versions), published_at=self.now()))
            for ordinal, (step_id, step_type, step_title) in enumerate(steps):
                session.add(LearningStepRecord(id=step_id, content_id=content_id, content_version=content_version, ordinal=ordinal, step_type=step_type, title=step_title, payload={}))
            for ordinal, (question_id, prompt, choices, correct, explanation) in enumerate(questions):
                session.add(ReviewQuestionRecord(id=question_id, content_id=content_id, content_version=content_version, ordinal=ordinal, prompt=prompt, choices=choices, correct_answer_key=correct, explanation=explanation))

    def content(self, content_id: str, version: str) -> LearningContentRecord | None:
        with self.database.session() as session:
            return session.get(LearningContentRecord, (content_id, version))

    def latest_content_version(self, content_id: str) -> str | None:
        with self.database.session() as session:
            return session.execute(select(LearningContentRecord.content_version).where(LearningContentRecord.id == content_id).order_by(LearningContentRecord.published_at.desc(), LearningContentRecord.content_version.desc())).scalars().first()

    def retire_content(self, content_id: str, version: str, *, security_critical: bool, resume_until: datetime | None) -> None:
        with self.database.session() as session:
            content = session.get(LearningContentRecord, (content_id, version))
            if content is None:
                raise ValueError("LEARNING_CONTENT_NOT_FOUND")
            content.status, content.retired_at = "retired", self.now()
            content.security_critical_retirement, content.resume_until = security_critical, resume_until

    def set_replacement(self, content_id: str, version: str, replacement_id: str, replacement_version: str) -> None:
        with self.database.session() as session:
            content = session.get(LearningContentRecord, (content_id, version))
            replacement = session.get(LearningContentRecord, (replacement_id, replacement_version))
            if content is None or replacement is None:
                raise ValueError("LEARNING_CONTENT_NOT_FOUND")
            content.replacement_content_id, content.replacement_content_version = replacement_id, replacement_version

    def start_session(self, employee_id: str, content_id: str, version: str) -> dict:
        now = self.now()
        with self.database.session() as session:
            record = session.execute(select(EmployeeLearningSessionRecord).where(EmployeeLearningSessionRecord.employee_identity_id == employee_id, EmployeeLearningSessionRecord.content_id == content_id, EmployeeLearningSessionRecord.content_version == version)).scalar_one_or_none()
            if record is None:
                content = session.get(LearningContentRecord, (content_id, version))
                record = EmployeeLearningSessionRecord(id=uuid4().hex, employee_identity_id=employee_id, content_id=content_id, content_version=version, question_version=content.question_version, lab_reference_versions=content.lab_reference_versions, status="in_progress", current_step_ordinal=0, started_at=now, last_activity_at=now)
                session.add(record)
                for step in self._steps(session, content_id, version):
                    session.add(StepProgressRecord(session_id=record.id, step_id=step.id, status="pending"))
                session.flush()
            return self._session_dict(session, record)

    def get_session(self, employee_id: str, session_id: str) -> dict | None:
        with self.database.session() as session:
            record = session.execute(select(EmployeeLearningSessionRecord).where(EmployeeLearningSessionRecord.id == session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one_or_none()
            return self._session_dict(session, record) if record else None

    def list_sessions(self, employee_id: str, roadmap_id: str) -> list[dict]:
        with self.database.session() as session:
            records = session.execute(select(EmployeeLearningSessionRecord).join(LearningContentRecord, (LearningContentRecord.id == EmployeeLearningSessionRecord.content_id) & (LearningContentRecord.content_version == EmployeeLearningSessionRecord.content_version)).where(EmployeeLearningSessionRecord.employee_identity_id == employee_id, LearningContentRecord.roadmap_id == roadmap_id).order_by(EmployeeLearningSessionRecord.started_at, EmployeeLearningSessionRecord.id)).scalars()
            return [self._session_dict(session, record) for record in records]

    def complete_step(self, employee_id: str, session_id: str, step_id: str) -> dict:
        now = self.now()
        with self.database.session() as session:
            record = session.execute(select(EmployeeLearningSessionRecord).where(EmployeeLearningSessionRecord.id == session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one()
            progress = session.get(StepProgressRecord, (session_id, step_id))
            if progress is None:
                raise ValueError("LEARNING_STEP_NOT_FOUND")
            progress.status, progress.completed_at = "completed", progress.completed_at or now
            steps = self._steps(session, record.content_id, record.content_version)
            progress_by_id = {item.step_id: item for item in session.execute(select(StepProgressRecord).where(StepProgressRecord.session_id == session_id)).scalars()}
            pending = next((step.ordinal for step in steps if progress_by_id[step.id].status != "completed"), len(steps))
            record.current_step_ordinal, record.last_activity_at = pending, now
            return self._session_dict(session, record)

    def start_attempt(self, employee_id: str, session_id: str) -> dict:
        now = self.now()
        with self.database.session() as session:
            learning = session.execute(select(EmployeeLearningSessionRecord).where(EmployeeLearningSessionRecord.id == session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one()
            if learning.status == "completed":
                raise ValueError("LEARNING_SESSION_COMPLETED")
            self._assert_review_allowed(session, learning)
            active = session.execute(select(ReviewAttemptRecord).where(ReviewAttemptRecord.session_id == session_id, ReviewAttemptRecord.status == "in_progress")).scalar_one_or_none()
            if active:
                return self._attempt_dict(session, active)
            recent = session.scalar(select(func.count()).select_from(ReviewAttemptRecord).where(ReviewAttemptRecord.session_id == session_id, ReviewAttemptRecord.started_at >= now - timedelta(minutes=60))) or 0
            if recent >= 5:
                raise OverflowError("REVIEW_RETRY_RATE_LIMITED")
            number = (session.scalar(select(func.max(ReviewAttemptRecord.attempt_number)).where(ReviewAttemptRecord.session_id == session_id)) or 0) + 1
            attempt = ReviewAttemptRecord(id=uuid4().hex, session_id=session_id, attempt_number=number, question_snapshot_version=learning.content_version, status="in_progress", started_at=now)
            session.add(attempt); session.flush()
            return self._attempt_dict(session, attempt)

    def answer(self, employee_id: str, attempt_id: str, question_id: str, answer_key: str) -> dict:
        now = self.now()
        with self.database.session() as session:
            attempt, learning = self._owned_attempt(session, employee_id, attempt_id)
            self._assert_review_allowed(session, learning)
            if attempt.status != "in_progress":
                raise ValueError("REVIEW_ATTEMPT_FINALIZED")
            question = session.execute(select(ReviewQuestionRecord).where(ReviewQuestionRecord.id == question_id, ReviewQuestionRecord.content_id == learning.content_id, ReviewQuestionRecord.content_version == learning.content_version)).scalar_one_or_none()
            if question is None:
                raise ValueError("REVIEW_QUESTION_VERSION_MISMATCH")
            if answer_key not in question.choices:
                raise ValueError("REVIEW_ANSWER_INVALID")
            existing = session.get(ReviewAnswerRecord, (attempt_id, question_id))
            if existing and existing.submitted_answer_key != answer_key:
                raise ValueError("REVIEW_ANSWER_IMMUTABLE")
            if existing is None:
                existing = ReviewAnswerRecord(attempt_id=attempt_id, question_id=question_id, submitted_answer_key=answer_key, is_correct=answer_key == question.correct_answer_key, explanation=question.explanation, answered_at=now)
                session.add(existing)
            return self._answer_dict(existing)

    def submit_attempt(self, employee_id: str, attempt_id: str) -> dict:
        now = self.now()
        with self.database.session() as session:
            attempt, learning = self._owned_attempt(session, employee_id, attempt_id)
            self._assert_review_allowed(session, learning)
            if attempt.status == "submitted":
                missed = [item.question_id for item in session.execute(select(ReviewAnswerRecord).where(ReviewAnswerRecord.attempt_id == attempt_id, ReviewAnswerRecord.is_correct.is_(False))).scalars()]
                return self._result_dict(attempt, learning.status, missed)
            questions = self._questions(session, learning.content_id, learning.content_version)
            answers = list(session.execute(select(ReviewAnswerRecord).where(ReviewAnswerRecord.attempt_id == attempt_id)).scalars())
            if len(answers) != len(questions):
                raise ValueError("REVIEW_ANSWERS_INCOMPLETE")
            correct = sum(item.is_correct for item in answers)
            score = correct / len(questions) * 100
            passed = score >= 80
            attempt.status, attempt.correct_count, attempt.question_count = "submitted", correct, len(questions)
            attempt.score_percent, attempt.passed, attempt.submitted_at = score, passed, now
            learning.status = "completed" if passed else "retry_required"
            learning.completed_at = learning.completed_at or (now if passed else None)
            learning.last_activity_at = now
            if passed:
                content = session.get(LearningContentRecord, (learning.content_id, learning.content_version))
                existing = session.execute(select(LearningMilestoneCompletionRecord).where(LearningMilestoneCompletionRecord.employee_identity_id == employee_id, LearningMilestoneCompletionRecord.roadmap_id == content.roadmap_id, LearningMilestoneCompletionRecord.milestone_key == content.milestone_key)).scalar_one_or_none()
                if existing is None:
                    session.add(LearningMilestoneCompletionRecord(id=uuid4().hex, employee_identity_id=employee_id, roadmap_id=content.roadmap_id, milestone_key=content.milestone_key, source_session_id=learning.id, completed_at=now))
            missed = [item.question_id for item in answers if not item.is_correct]
            return self._result_dict(attempt, learning.status, missed)

    def milestone_completion_count(self, employee_id: str, roadmap_id: str, milestone_key: str) -> int:
        with self.database.session() as session:
            return session.scalar(select(func.count()).select_from(LearningMilestoneCompletionRecord).where(LearningMilestoneCompletionRecord.employee_identity_id == employee_id, LearningMilestoneCompletionRecord.roadmap_id == roadmap_id, LearningMilestoneCompletionRecord.milestone_key == milestone_key)) or 0

    def reload_lab_state(self, employee_id: str, session_id: str, lab_reference_version: str, availability: str, cost_status: str) -> dict:
        now = self.now()
        with self.database.session() as session:
            learning = session.execute(select(EmployeeLearningSessionRecord).where(EmployeeLearningSessionRecord.id == session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one()
            if lab_reference_version not in learning.lab_reference_versions:
                raise ValueError("LAB_REFERENCE_VERSION_NOT_PINNED")
            state = session.get(LearningLabStateRecord, (session_id, lab_reference_version))
            if state is None:
                state = LearningLabStateRecord(session_id=session_id, lab_reference_version=lab_reference_version, availability_state_snapshot=availability, cost_status_snapshot=cost_status, last_reloaded_at=now)
                session.add(state)
            else:
                state.availability_state_snapshot, state.cost_status_snapshot, state.last_reloaded_at = availability, cost_status, now
            return {"lab_reference_version": lab_reference_version, "availability_state": availability, "cost_status": cost_status, "last_reloaded_at": now}

    def get_lab_state(self, employee_id: str, session_id: str, lab_reference_version: str) -> dict | None:
        with self.database.session() as session:
            session.execute(select(EmployeeLearningSessionRecord.id).where(EmployeeLearningSessionRecord.id == session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one()
            state = session.get(LearningLabStateRecord, (session_id, lab_reference_version))
            if state is None:
                return None
            return {"lab_reference_version": state.lab_reference_version, "availability_state": state.availability_state_snapshot, "cost_status": state.cost_status_snapshot, "opened_at": state.opened_at, "last_reloaded_at": state.last_reloaded_at, "reported_at": state.reported_at}

    def report_lab(self, employee_id: str, session_id: str, lab_reference_version: str, reason: str, comment: str | None = None) -> dict:
        if reason not in {"unavailable", "unsuitable", "cost_mismatch", "other"}:
            raise ValueError("LAB_REPORT_REASON_INVALID")
        now = self.now()
        with self.database.session() as session:
            learning = session.execute(select(EmployeeLearningSessionRecord).where(EmployeeLearningSessionRecord.id == session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one()
            if lab_reference_version not in learning.lab_reference_versions:
                raise ValueError("LAB_REFERENCE_VERSION_NOT_PINNED")
            report = LearningLabReportRecord(id=uuid4().hex, session_id=session_id, employee_identity_id=employee_id, lab_reference_version=lab_reference_version, reason=reason, comment=comment, created_at=now)
            session.add(report)
            state = session.get(LearningLabStateRecord, (session_id, lab_reference_version))
            if state is not None:
                state.reported_at = state.reported_at or now
            return {"id": report.id, "lab_reference_version": lab_reference_version, "reason": reason, "created_at": now}

    def start_required_clock(self, employee_id: str, session_id: str, started_at: datetime, reason: str = "required_content") -> str:
        with self.database.session() as session:
            session.execute(select(EmployeeLearningSessionRecord.id).where(EmployeeLearningSessionRecord.id == session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one()
            active = session.execute(select(RequiredClockSegmentRecord).where(RequiredClockSegmentRecord.session_id == session_id, RequiredClockSegmentRecord.ended_at.is_(None))).scalar_one_or_none()
            if active:
                return active.id
            segment_id = uuid4().hex
            session.add(RequiredClockSegmentRecord(id=segment_id, session_id=session_id, reason=reason, started_at=started_at))
            return segment_id

    def pause_required_clock(self, employee_id: str, session_id: str, ended_at: datetime, reason: str) -> dict:
        with self.database.session() as session:
            session.execute(select(EmployeeLearningSessionRecord.id).where(EmployeeLearningSessionRecord.id == session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one()
            active = session.execute(select(RequiredClockSegmentRecord).where(RequiredClockSegmentRecord.session_id == session_id, RequiredClockSegmentRecord.ended_at.is_(None))).scalar_one_or_none()
            if active is None:
                raise ValueError("REQUIRED_CLOCK_MISSING")
            start = active.started_at.replace(tzinfo=timezone.utc) if active.started_at.tzinfo is None else active.started_at
            end = ended_at.replace(tzinfo=timezone.utc) if ended_at.tzinfo is None else ended_at
            if end < start:
                raise ValueError("REQUIRED_CLOCK_NEGATIVE_SEGMENT")
            active.ended_at, active.duration_ms, active.reason = ended_at, int((end - start).total_seconds() * 1000), reason
            return {"id": active.id, "reason": reason, "duration_ms": active.duration_ms}

    def list_attempts(self, employee_id: str, session_id: str) -> list[dict]:
        with self.database.session() as session:
            session.execute(select(EmployeeLearningSessionRecord.id).where(EmployeeLearningSessionRecord.id == session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one()
            attempts = list(session.execute(select(ReviewAttemptRecord).where(ReviewAttemptRecord.session_id == session_id).order_by(ReviewAttemptRecord.attempt_number, ReviewAttemptRecord.id)).scalars())
            restored = [self._attempt_dict(session, attempt) for attempt in attempts]
            highest = max((item["score_percent"] for item in restored if item["score_percent"] is not None), default=None)
            return [{**item, "latest": index == len(restored) - 1, "highest": highest is not None and item["score_percent"] == highest} for index, item in enumerate(restored)]

    def get_attempt(self, employee_id: str, attempt_id: str) -> dict | None:
        with self.database.session() as session:
            attempt = session.get(ReviewAttemptRecord, attempt_id)
            if attempt is None:
                return None
            learning = session.get(EmployeeLearningSessionRecord, attempt.session_id)
            if learning is None or learning.employee_identity_id != employee_id:
                return None
            return self._attempt_dict(session, attempt)

    def learning_candidates(self, employee_id: str, roadmap_id: str) -> list[PersistedLearningCandidate]:
        with self.database.session() as session:
            rows = session.execute(select(EmployeeLearningSessionRecord, LearningContentRecord).join(LearningContentRecord, (LearningContentRecord.id == EmployeeLearningSessionRecord.content_id) & (LearningContentRecord.content_version == EmployeeLearningSessionRecord.content_version)).where(EmployeeLearningSessionRecord.employee_identity_id == employee_id, LearningContentRecord.roadmap_id == roadmap_id, EmployeeLearningSessionRecord.status.in_(("retry_required", "in_progress")))).all()
            return [PersistedLearningCandidate("retry_material" if learning.status == "retry_required" else "resume_session", roadmap_id, content.milestone_key, content.title, learning.current_step_ordinal, learning.started_at.isoformat(), learning.id) for learning, content in rows]

    @staticmethod
    def _steps(session, content_id, version):
        return list(session.execute(select(LearningStepRecord).where(LearningStepRecord.content_id == content_id, LearningStepRecord.content_version == version).order_by(LearningStepRecord.ordinal, LearningStepRecord.id)).scalars())

    @staticmethod
    def _questions(session, content_id, version):
        return list(session.execute(select(ReviewQuestionRecord).where(ReviewQuestionRecord.content_id == content_id, ReviewQuestionRecord.content_version == version).order_by(ReviewQuestionRecord.ordinal, ReviewQuestionRecord.id)).scalars())

    def _session_dict(self, session, record):
        content = session.get(LearningContentRecord, (record.content_id, record.content_version))
        progress = {item.step_id: item for item in session.execute(select(StepProgressRecord).where(StepProgressRecord.session_id == record.id)).scalars()}
        resume_until = content.resume_until
        if resume_until is not None and resume_until.tzinfo is None:
            resume_until = resume_until.replace(tzinfo=timezone.utc)
        return {"id": record.id, "roadmap_id": content.roadmap_id, "content_id": record.content_id, "content_version": record.content_version, "question_version": record.question_version, "lab_reference_versions": record.lab_reference_versions, "title": content.title, "objective": content.objective, "estimated_minutes": content.estimated_minutes, "status": record.status, "current_step_ordinal": record.current_step_ordinal, "retirement": {"status": content.status, "security_critical": content.security_critical_retirement, "resume_until": resume_until, "replacement_content_id": content.replacement_content_id, "replacement_content_version": content.replacement_content_version}, "steps": [{"id": step.id, "ordinal": step.ordinal, "step_type": step.step_type, "title": step.title, "status": progress[step.id].status} for step in self._steps(session, record.content_id, record.content_version)]}

    def _attempt_dict(self, session, attempt):
        learning = session.get(EmployeeLearningSessionRecord, attempt.session_id)
        answers = list(session.execute(select(ReviewAnswerRecord).where(ReviewAnswerRecord.attempt_id == attempt.id)).scalars())
        return {"id": attempt.id, "attempt_number": attempt.attempt_number, "status": attempt.status, "question_snapshot_version": attempt.question_snapshot_version, "questions": [{"id": item.id, "ordinal": item.ordinal, "prompt": item.prompt, "choices": item.choices} for item in self._questions(session, learning.content_id, learning.content_version)], "answers": [self._answer_dict(item) for item in answers], "started_at": attempt.started_at, "score_percent": attempt.score_percent, "passed": attempt.passed, "submitted_at": attempt.submitted_at}

    @staticmethod
    def _answer_dict(answer):
        answered_at = answer.answered_at
        if answered_at.tzinfo is None:
            answered_at = answered_at.replace(tzinfo=timezone.utc)
        return {"question_id": answer.question_id, "submitted_answer_key": answer.submitted_answer_key, "correct": answer.is_correct, "explanation": answer.explanation, "answered_at": answered_at}

    @staticmethod
    def _result_dict(attempt, session_status, missed_question_ids):
        return {"attempt_id": attempt.id, "score_percent": attempt.score_percent, "passed": attempt.passed, "session_status": session_status, "missed_question_ids": missed_question_ids, "next_action": "continue_learning" if attempt.passed else "review_missed_concepts"}

    @staticmethod
    def _owned_attempt(session, employee_id, attempt_id):
        attempt = session.get(ReviewAttemptRecord, attempt_id)
        if attempt is None:
            raise ValueError("REVIEW_ATTEMPT_NOT_FOUND")
        learning = session.execute(select(EmployeeLearningSessionRecord).where(EmployeeLearningSessionRecord.id == attempt.session_id, EmployeeLearningSessionRecord.employee_identity_id == employee_id)).scalar_one()
        return attempt, learning

    @staticmethod
    def _assert_review_allowed(session, learning) -> None:
        content = session.get(LearningContentRecord, (learning.content_id, learning.content_version))
        if content.security_critical_retirement:
            raise ValueError("CONTENT_VERSION_SECURITY_RETIRED")
