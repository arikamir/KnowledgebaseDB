"""Roadmap revision snapshots used by progress updates."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from knowledge.schemas import CareerRoadmap, utcnow


class RoadmapRevision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prior_roadmap: CareerRoadmap
    updated_roadmap: CareerRoadmap
    completed_steps: list[str] = Field(default_factory=list)
    normalized_milestone_keys: list[str] = Field(default_factory=list)
    new_goals: list[str] = Field(default_factory=list)
    summary: str
    created_at: datetime = Field(default_factory=utcnow)
