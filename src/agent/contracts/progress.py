"""Contracts for progress check-ins and roadmap revisions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent.roadmap_revision import RoadmapRevision
from knowledge.schemas import EmployeeProfile, ProgressCheckIn


class ProgressCheckInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_profile_id: str
    roadmap_id: str
    notes: str = ""
    completed_steps: list[str] = Field(default_factory=list)
    new_goals: list[str] = Field(default_factory=list)

    @field_validator("employee_profile_id", "roadmap_id", mode="before")
    @classmethod
    def _normalize_required_text(cls, value: object) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("identifier must not be empty")
        return text

    @field_validator("notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("completed_steps", "new_goals", mode="before")
    @classmethod
    def _coerce_lists(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = [item.strip() for item in value.split(",")]
            return [item for item in parts if item]
        return [str(item).strip() for item in value if str(item).strip()]


class ProgressReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: RoadmapRevision
    presentation: str
    follow_up_prompt: str
    check_in: ProgressCheckIn | None = None

