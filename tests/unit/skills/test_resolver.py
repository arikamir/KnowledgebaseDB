from __future__ import annotations

from skills.catalog import SkillCatalog
from skills.resolver import resolve_topic


def test_resolver_handles_supported_aliases():
    catalog = SkillCatalog.load()

    resolution = resolve_topic("Docker-Compose", catalog)

    assert resolution.supported
    assert resolution.canonical_topic == "Docker Compose"


def test_resolver_suggests_supported_topics_for_unknown_input():
    catalog = SkillCatalog.load()

    resolution = resolve_topic("Kubernets", catalog)

    assert not resolution.supported
    assert resolution.suggested_topics
    assert "Kubernetes" in resolution.suggested_topics


def test_resolver_flags_inactive_topics_as_newly_added():
    from knowledge.schemas import SkillArea

    topic = SkillArea(
        name="Experimental Platform",
        category="Emerging",
        description="New topic",
        is_active=False,
        current_level_fit="Experimental",
        practical_next_action="Try a pilot",
    )
    catalog = SkillCatalog(topics=[topic])

    resolution = resolve_topic("Experimental Platform", catalog)

    assert not resolution.supported
    assert resolution.newly_added
    assert resolution.canonical_topic == "Experimental Platform"

