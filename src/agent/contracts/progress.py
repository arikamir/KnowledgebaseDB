"""Contracts for progress check-ins and roadmap revisions."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from agent.roadmap_revision import RoadmapRevision
from knowledge.schemas import ProgressCheckIn, RoadmapStep


MilestoneKey = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9][a-z0-9._-]{2,127}$"),
]


class ProgressCheckInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_profile_id: str | None = None
    roadmap_id: str
    notes: str = ""
    completed_steps: list[str] = Field(default_factory=list)
    completed_milestone_keys: list[MilestoneKey] = Field(default_factory=list)
    new_goals: list[str] = Field(default_factory=list)

    @field_validator("roadmap_id", mode="before")
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

    @field_validator("completed_steps", "completed_milestone_keys", "new_goals", mode="before")
    @classmethod
    def _coerce_lists(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = [item.strip() for item in value.split(",")]
            return [item for item in parts if item]
        return [str(item).strip() for item in value if str(item).strip()]


class NextActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    title: str
    reason: str
    target: str


class ProgressReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: RoadmapRevision
    presentation: str
    follow_up_prompt: str
    check_in: ProgressCheckIn | None = None
    roadmap_id: str
    current_status: str
    gaps: list[str] = Field(default_factory=list)
    milestones: list[RoadmapStep] = Field(min_length=1)
    next_action: NextActionResponse
