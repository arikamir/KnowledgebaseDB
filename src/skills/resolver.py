"""Topic normalization and unsupported-topic fallback logic."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from knowledge.schemas import SkillArea
from skills.catalog import SkillCatalog


class TopicResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_topic: str
    canonical_topic: str | None = None
    supported: bool
    newly_added: bool = False
    suggested_topics: list[str] = Field(default_factory=list)
    reason: str


def resolve_topic(topic: str, catalog: SkillCatalog) -> TopicResolution:
    requested = topic.strip()
    if not requested:
        return TopicResolution(
            requested_topic=topic,
            supported=False,
            reason="No topic name was supplied.",
            suggested_topics=catalog.topic_names(),
        )

    active = catalog.get_active(requested)
    if active:
        return TopicResolution(
            requested_topic=requested,
            canonical_topic=active.name,
            supported=True,
            reason=f"{active.name} is a supported skill area.",
            suggested_topics=catalog.related_topics(active.name),
        )

    inactive = catalog.inactive_match(requested)
    if inactive:
        return TopicResolution(
            requested_topic=requested,
            canonical_topic=inactive.name,
            supported=False,
            newly_added=True,
            reason=f"{inactive.name} is recognized but not active yet.",
            suggested_topics=catalog.related_topics(inactive.name),
        )

    suggestions = catalog.suggest(requested)
    return TopicResolution(
        requested_topic=requested,
        supported=False,
        reason="The requested topic is not in the active catalog.",
        suggested_topics=suggestions,
    )


def normalize_topic(topic: str, catalog: SkillCatalog) -> str:
    resolution = resolve_topic(topic, catalog)
    return resolution.canonical_topic or topic.strip()

