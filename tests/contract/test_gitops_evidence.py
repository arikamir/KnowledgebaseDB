from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_evidence_schema_is_closed_and_redaction_aware() -> None:
    schema = json.loads((ROOT / "config/gitops-evidence.schema.json").read_text())
    assert schema["$id"].endswith("gitops-evidence-v2.json")
    assert schema["properties"]["schemaVersion"] == {"const": 2}
    assert schema["additionalProperties"] is False
    assert "automatedReview" in schema["required"]
    assert "timing" in schema["required"]


def test_collector_requires_release_and_contains_audit_fields() -> None:
    script = (ROOT / "scripts/ci/collect-argocd-evidence.sh").read_text()
    assert "schemaVersion:2" in script
    assert "--automated-reviewer must identify the reviewer that passed the current-head gate" in script
    assert 'AUTOMATED_REVIEWER=""' in script
    assert "credential-shaped content is forbidden" in script
    assert "humanAction" in script
    assert "rollback" in script
    assert "GITOPS_AFFECTED_SERVICE" in script
