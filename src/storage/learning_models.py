"""Pinned learning-session and immutable review persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from storage.database import Base, utcnow


class LearningContentRecord(Base):
    __tablename__ = "learning_content"
    __table_args__ = (UniqueConstraint("id", "content_version", name="uq_learning_content_version"), CheckConstraint("estimated_minutes BETWEEN 20 AND 30", name="ck_learning_estimate"), CheckConstraint("status IN ('draft','published','retired')", name="ck_learning_content_status"))
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    roadmap_id: Mapped[str] = mapped_column(String(64), nullable=False)
    milestone_key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    objective: Mapped[str] = mapped_column(String(1024), nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="published", nullable=False)
    body_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    question_version: Mapped[str] = mapped_column(String(64), nullable=False)
    lab_reference_versions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resume_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retirement_reason: Mapped[str | None] = mapped_column(String(512))
    security_critical_retirement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class LearningStepRecord(Base):
    __tablename__ = "learning_steps"
    __table_args__ = (UniqueConstraint("content_id", "content_version", "ordinal", name="uq_learning_step_ordinal"), CheckConstraint("step_type IN ('reading','activity','lab','review')", name="ck_learning_step_type"))
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_version: Mapped[str] = mapped_column(String(64), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ReviewQuestionRecord(Base):
    __tablename__ = "review_questions"
    __table_args__ = (UniqueConstraint("content_id", "content_version", "ordinal", name="uq_review_question_ordinal"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_version: Mapped[str] = mapped_column(String(64), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    correct_answer_key: Mapped[str] = mapped_column(String(64), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class EmployeeLearningSessionRecord(Base):
    __tablename__ = "employee_learning_sessions"
    __table_args__ = (UniqueConstraint("employee_identity_id", "content_id", "content_version", name="uq_employee_pinned_session"), CheckConstraint("status IN ('not_started','in_progress','retry_required','completed')", name="ck_learning_session_status"))
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_identity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_version: Mapped[str] = mapped_column(String(64), nullable=False)
    question_version: Mapped[str] = mapped_column(String(64), nullable=False)
    lab_reference_versions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="in_progress", nullable=False)
    current_step_ordinal: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StepProgressRecord(Base):
    __tablename__ = "learning_step_progress"
    session_id: Mapped[str] = mapped_column(ForeignKey("employee_learning_sessions.id", ondelete="CASCADE"), primary_key=True)
    step_id: Mapped[str] = mapped_column(ForeignKey("learning_steps.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearningLabStateRecord(Base):
    __tablename__ = "learning_lab_state"
    session_id: Mapped[str] = mapped_column(ForeignKey("employee_learning_sessions.id", ondelete="CASCADE"), primary_key=True)
    lab_reference_version: Mapped[str] = mapped_column(String(128), primary_key=True)
    availability_state_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    cost_status_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewAttemptRecord(Base):
    __tablename__ = "review_attempts"
    __table_args__ = (
        UniqueConstraint("session_id", "attempt_number", name="uq_review_attempt_number"),
        CheckConstraint("status IN ('in_progress','submitted')", name="ck_review_attempt_status"),
        Index("uq_review_one_in_progress", "session_id", unique=True, sqlite_where=text("status = 'in_progress'"), postgresql_where=text("status = 'in_progress'")),
        Index("ix_review_retry_window", "session_id", "started_at"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("employee_learning_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_snapshot_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="in_progress", nullable=False)
    correct_count: Mapped[int | None] = mapped_column(Integer)
    question_count: Mapped[int | None] = mapped_column(Integer)
    score_percent: Mapped[float | None] = mapped_column(Float)
    passed: Mapped[bool | None] = mapped_column(Boolean)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewAnswerRecord(Base):
    __tablename__ = "review_answers"
    attempt_id: Mapped[str] = mapped_column(ForeignKey("review_attempts.id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("review_questions.id"), primary_key=True)
    submitted_answer_key: Mapped[str] = mapped_column(String(64), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class LearningMilestoneCompletionRecord(Base):
    __tablename__ = "learning_milestone_completions"
    __table_args__ = (UniqueConstraint("employee_identity_id", "roadmap_id", "milestone_key", name="uq_learning_milestone_completion"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_identity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    roadmap_id: Mapped[str] = mapped_column(String(64), nullable=False)
    milestone_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_session_id: Mapped[str] = mapped_column(ForeignKey("employee_learning_sessions.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RequiredClockSegmentRecord(Base):
    __tablename__ = "learning_required_clock_segments"
    __table_args__ = (CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_required_clock_nonnegative"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("employee_learning_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class LearningActivityEventRecord(Base):
    __tablename__ = "learning_activity_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_identity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    roadmap_id: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str] = mapped_column(ForeignKey("employee_learning_sessions.id", ondelete="CASCADE"), nullable=False)
    content_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128))
    trace_id: Mapped[str | None] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
