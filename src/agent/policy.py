"""Boundary detection for HR and performance-management requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


HR_KEYWORDS = {
    "hr",
    "human resources",
    "performance review",
    "review cycle",
    "salary",
    "compensation",
    "bonus",
    "promotion",
    "disciplinary",
    "termination",
    "performance plan",
    "rank",
}

PERFORMANCE_KEYWORDS = {
    "manager rating",
    "employee evaluation",
    "evaluation",
    "okr",
    "kpi",
    "rating",
    "calibration",
    "performance score",
}


def _find_matches(text: str, keywords: Iterable[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


@dataclass(slots=True)
class BoundaryDecision:
    allowed: bool
    category: str | None
    reason: str
    matched_terms: list[str] = field(default_factory=list)
    suggested_action: str | None = None


def classify_request(text: str) -> BoundaryDecision:
    """Return a boundary decision for a free-form user request."""

    matches = _find_matches(text, PERFORMANCE_KEYWORDS)
    if matches:
        return BoundaryDecision(
            allowed=False,
            category="performance",
            reason="Request appears to involve employee evaluation or performance management.",
            matched_terms=matches,
            suggested_action="Keep the response focused on growth guidance and learning steps.",
        )

    matches = _find_matches(text, HR_KEYWORDS)
    if matches:
        return BoundaryDecision(
            allowed=False,
            category="hr",
            reason="Request appears to involve HR or compensation decisions.",
            matched_terms=matches,
            suggested_action="Provide general career guidance instead of policy or evaluation advice.",
        )

    return BoundaryDecision(
        allowed=True,
        category=None,
        reason="Request stays within career guidance boundaries.",
        matched_terms=[],
        suggested_action=None,
    )


def is_boundary_violation(text: str) -> bool:
    return not classify_request(text).allowed
