"""Contracts for roadmap intake and roadmap responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from knowledge.schemas import CareerRoadmap, EmployeeProfile, make_id


class ClarifyingQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=make_id)
    prompt: str
    why_it_matters: str

    @field_validator("prompt", "why_it_matters", mode="before")
    @classmethod
    def _normalize_text(cls, value: object) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("clarifying question text must not be empty")
        return text


class RoadmapIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_profile: EmployeeProfile = Field(default_factory=EmployeeProfile)
    request_text: str | None = None
    clarifying_questions_asked: int = 0

    @field_validator("request_text", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("clarifying_questions_asked", mode="before")
    @classmethod
    def _coerce_question_count(cls, value: object) -> int:
        if value in (None, ""):
            return 0
        return max(0, int(value))


class RoadmapIntakeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["needs_more_info", "ready"]
    employee_profile_id: str | None = None
    roadmap_id: str | None = None
    roadmap: CareerRoadmap | None = None
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    presentation: str = ""
    follow_up_prompt: str = ""

