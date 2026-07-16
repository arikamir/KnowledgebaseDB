"""Deterministic Foundation next-action selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class MilestoneCandidate:
    roadmap_id: str
    milestone_key: str
    ordinal: int
    title: str
    completed: bool = False


@dataclass(frozen=True, slots=True)
class NextAction:
    action_type: str
    roadmap_id: str
    milestone_key: str | None
    title: str


def select_foundation_next_action(roadmap_id: str, milestones: Iterable[MilestoneCandidate]) -> NextAction:
    ordered = sorted(milestones, key=lambda item: (item.ordinal, item.milestone_key))
    pending = next((item for item in ordered if not item.completed), None)
    if pending:
        return NextAction("continue_milestone", roadmap_id, pending.milestone_key, pending.title)
    return NextAction("review_roadmap", roadmap_id, None, "Review your completed roadmap")
