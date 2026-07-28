from __future__ import annotations

from skills.catalog import SkillCatalog


def test_catalog_loads_seeded_topics():
    catalog = SkillCatalog.load()

    names = catalog.topic_names()
    assert "GitHub Actions" in names
    assert "Kubernetes" in names
    assert len(names) == len(set(names))


def test_catalog_resolves_aliases():
    catalog = SkillCatalog.load()

    assert catalog.get("Opeshift").name == "OpenShift"
    assert catalog.get("DotNet").name == ".NET"
    assert catalog.get("hashicorp vault").name == "HashiCorp Vault"

