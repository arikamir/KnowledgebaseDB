"""Core feature schemas for the DevOps career agent."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def make_id() -> str:
    return uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def enum_text(value: Any) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


class ExperienceLevel(str, Enum):
    UNKNOWN = "unknown"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    LEAD = "lead"


class TimeHorizon(str, Enum):
    IMMEDIATE = "immediate"
    NEAR_TERM = "near_term"
    LONG_TERM = "long_term"


class CompletionState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RoadmapStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    REVISED = "revised"
    COMPLETED = "completed"


class EmployeeProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    id: str = Field(default_factory=make_id)
    role: str | None = None
    experience_level: ExperienceLevel | str | None = None
    target_role: str | None = None
    target_specializations: list[str] = Field(default_factory=list)
    available_time_per_week: int | None = None
    learning_preferences: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("role", "target_role", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("target_specializations", "learning_preferences", "constraints", mode="before")
    @classmethod
    def _coerce_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
            return [item for item in items if item]
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("available_time_per_week", mode="before")
    @classmethod
    def _coerce_time(cls, value: Any) -> int | None:
        if value in (None, ""):
            return None
        return int(value)

    @model_validator(mode="after")
    def _validate(self) -> "EmployeeProfile":
        if self.available_time_per_week is not None and self.available_time_per_week < 0:
            raise ValueError("available_time_per_week must be non-negative")
        return self

    def missing_core_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.role:
            missing.append("role")
        if not self.experience_level:
            missing.append("experience_level")
        if not self.target_role:
            missing.append("target_role")
        if self.available_time_per_week is None:
            missing.append("available_time_per_week")
        return missing

    def normalized_text(self) -> str:
        parts = [
            self.role or "",
            str(self.experience_level or ""),
            self.target_role or "",
            " ".join(self.target_specializations),
            " ".join(self.learning_preferences),
            " ".join(self.constraints),
        ]
        return " ".join(part for part in parts if part).strip().lower()


class SkillArea(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    id: str = Field(default_factory=make_id)
    name: str
    category: str
    description: str
    related_skills: list[str] = Field(default_factory=list)
    priority_level: int = 0
    is_active: bool = True
    aliases: list[str] = Field(default_factory=list)
    current_level_fit: str = ""
    practical_next_action: str = ""
    common_pitfalls: list[str] = Field(default_factory=list)

    @field_validator("name", "category", "description", "current_level_fit", "practical_next_action", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("text fields must not be empty")
        return text

    @field_validator("related_skills", "aliases", "common_pitfalls", mode="before")
    @classmethod
    def _coerce_text_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
            return [item for item in items if item]
        return [str(item).strip() for item in value if str(item).strip()]


class RoadmapStep(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    id: str = Field(default_factory=make_id)
    title: str
    skill_area: str
    experience_level_fit: str
    time_horizon: TimeHorizon
    concrete_next_action: str
    reason_it_matters: str
    priority: int = 0
    completion_state: CompletionState = CompletionState.PENDING
    supporting_notes: list[str] = Field(default_factory=list)

    @field_validator(
        "title",
        "skill_area",
        "experience_level_fit",
        "concrete_next_action",
        "reason_it_matters",
        mode="before",
    )
    @classmethod
    def _normalize_required_text(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("text fields must not be empty")
        return text

    @field_validator("supporting_notes", mode="before")
    @classmethod
    def _coerce_notes(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
            return [item for item in items if item]
        return [str(item).strip() for item in value if str(item).strip()]


class CareerRoadmap(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    id: str = Field(default_factory=make_id)
    employee_profile_id: str
    previous_roadmap_id: str | None = None
    goal_summary: str
    current_focus: str
    milestones: list[RoadmapStep] = Field(default_factory=list)
    next_actions: list[RoadmapStep] = Field(default_factory=list)
    status: RoadmapStatus = RoadmapStatus.DRAFT
    assumptions: list[str] = Field(default_factory=list)
    clarifying_questions_asked: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("goal_summary", "current_focus", mode="before")
    @classmethod
    def _normalize_goal_text(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("text fields must not be empty")
        return text

    @field_validator("assumptions", mode="before")
    @classmethod
    def _coerce_assumptions(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split("\n") if item.strip()]
        return [str(item).strip() for item in value if str(item).strip()]

    @model_validator(mode="after")
    def _validate_horizons(self) -> "CareerRoadmap":
        horizons = {enum_text(step.time_horizon) for step in self.milestones}
        if TimeHorizon.IMMEDIATE.value not in horizons:
            raise ValueError("roadmap must include at least one immediate step")
        if TimeHorizon.LONG_TERM.value not in horizons:
            raise ValueError("roadmap must include at least one long-term step")
        if not self.next_actions:
            self.next_actions = [
                step for step in self.milestones if enum_text(step.time_horizon) != TimeHorizon.LONG_TERM.value
            ]
        return self


class ProgressCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    id: str = Field(default_factory=make_id)
    employee_profile_id: str
    roadmap_id: str
    notes: str = ""
    completed_steps: list[str] = Field(default_factory=list)
    new_goals: list[str] = Field(default_factory=list)
    updated_recommendations: list[RoadmapStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("completed_steps", "new_goals", mode="before")
    @classmethod
    def _coerce_text_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
            return [item for item in items if item]
        return [str(item).strip() for item in value if str(item).strip()]
