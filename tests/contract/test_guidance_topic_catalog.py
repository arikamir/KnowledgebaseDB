from pathlib import Path

import yaml

from skills.catalog import SkillCatalog


ROOT = Path(__file__).resolve().parents[2]


def test_runtime_catalog_matches_authoritative_version_order_and_states() -> None:
    authoritative = yaml.safe_load((ROOT / "specs/003-develop-ui/contracts/supported-guidance-topics-v1.yaml").read_text())
    generated = yaml.safe_load((ROOT / "config/supported-guidance-topics-v1.yaml").read_text())
    assert generated == authoritative
    ids = [item["id"] for item in generated["topics"]]
    assert len(ids) == len(set(ids))
    catalog = SkillCatalog.load(ROOT / "config/supported-guidance-topics-v1.yaml")
    assert catalog.catalog_version == generated["catalog_version"]
    assert catalog.topic_state("K8S") == "active"
