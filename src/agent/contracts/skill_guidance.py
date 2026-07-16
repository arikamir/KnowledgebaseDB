"""Contracts for skill-specific guidance requests and responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from knowledge.schemas import EmployeeProfile


class TopicGuidanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    employee_profile: EmployeeProfile = Field(default_factory=EmployeeProfile)
    request_text: str | None = None


class SkillGuidanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_topic: str
    resolved_topic: str | None = None
    supported: bool
    topic_summary: str
    current_level_fit: str
    practical_next_action: str
    lab_references: list[dict[str, object]] = Field(default_factory=list)
    common_pitfalls: list[str] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TopicGuidanceEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "fallback"] = "ready"
    guidance: SkillGuidanceResponse
