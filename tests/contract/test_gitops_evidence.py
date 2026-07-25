from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_evidence_schema_is_closed_and_redaction_aware() -> None:
    schema = json.loads((ROOT / "config/gitops-evidence.schema.json").read_text())
    assert schema["additionalProperties"] is False
    assert "copilotReview" in schema["required"]
    assert "timing" in schema["required"]


def test_collector_requires_release_and_contains_audit_fields() -> None:
    script = (ROOT / "scripts/ci/collect-argocd-evidence.sh").read_text()
    assert "credential-shaped content is forbidden" in script
    assert "humanAction" in script
    assert "rollback" in script
    assert "GITOPS_AFFECTED_SERVICE" in script
