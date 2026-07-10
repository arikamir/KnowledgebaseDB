"""Skill-specific guidance generation."""

from __future__ import annotations

from dataclasses import dataclass

from agent.contracts.skill_guidance import SkillGuidanceResponse, TopicGuidanceRequest
from skills.catalog import SkillCatalog
from skills.resolver import TopicResolution, resolve_topic


@dataclass(slots=True)
class SkillGuidanceService:
    catalog: SkillCatalog

    def generate_guidance(self, request: TopicGuidanceRequest) -> SkillGuidanceResponse:
        resolution = resolve_topic(request.topic, self.catalog)
        if not resolution.supported:
            return self._fallback_guidance(request, resolution)

        topic = self.catalog.get(resolution.canonical_topic or request.topic)
        if topic is None:
            return self._fallback_guidance(request, resolution)

        experience_level = str(request.employee_profile.experience_level or "unknown")
        topic_summary = topic.description
        fit = f"{topic.current_level_fit} Current context: {experience_level}."
        next_action = topic.practical_next_action

        if request.employee_profile.target_role:
            next_action = f"{next_action} Aim it toward {request.employee_profile.target_role}."

        notes = [resolution.reason]
        if request.request_text:
            notes.append("Tailored to the question the employee asked.")

        return SkillGuidanceResponse(
            requested_topic=request.topic,
            resolved_topic=topic.name,
            supported=True,
            topic_summary=topic_summary,
            current_level_fit=fit,
            practical_next_action=next_action,
            common_pitfalls=list(topic.common_pitfalls),
            related_topics=self.catalog.related_topics(topic.name),
            suggestions=[],
            notes=notes,
        )

    def _fallback_guidance(
        self, request: TopicGuidanceRequest, resolution: TopicResolution
    ) -> SkillGuidanceResponse:
        suggestions = resolution.suggested_topics or self.catalog.topic_names()
        closest = suggestions[0] if suggestions else None
        topic_summary = (
            f"{request.topic} is not covered yet. "
            f"Closest supported topics: {', '.join(suggestions[:3]) if suggestions else 'none'}."
        )
        next_action = (
            f"Use the closest supported topic next: {closest}."
            if closest
            else "Pick one of the active DevOps topics and continue from there."
        )
        fit = "General career guidance only; topic-specific detail is not available yet."
        notes = [resolution.reason, "No detailed guidance is available for unsupported topics."]
        if resolution.newly_added:
            notes.append("The topic is recognized but not active yet.")

        return SkillGuidanceResponse(
            requested_topic=request.topic,
            resolved_topic=resolution.canonical_topic,
            supported=False,
            topic_summary=topic_summary,
            current_level_fit=fit,
            practical_next_action=next_action,
            common_pitfalls=[],
            related_topics=suggestions[:3],
            suggestions=suggestions[:3],
            notes=notes,
        )

