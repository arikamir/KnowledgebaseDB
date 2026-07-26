from __future__ import annotations

import json
import subprocess
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
    assert "--automated-review-evidence must be a receipt produced by the current-head gate" in script
    assert "--automated-reviewer" not in script
    assert "--automated-review-status" not in script
    assert '"approved-review"' in script
    assert '"no-findings-reaction"' in script
    assert "credential-shaped content is forbidden" in script
    assert "humanAction" in script
    assert "rollback" in script
    assert "GITOPS_AFFECTED_SERVICE" in script


def test_collector_consumes_successful_gate_receipt(tmp_path: Path) -> None:
    output = tmp_path / "evidence.json"
    result = subprocess.run(
        [
            str(ROOT / "scripts/ci/collect-argocd-evidence.sh"),
            "--release",
            str(ROOT / "tests/contract/fixtures/gitops/release-manifest.json"),
            "--automated-review-evidence",
            str(ROOT / "tests/contract/fixtures/gitops/valid-automated-review-evidence.json"),
            "--review-pull-request",
            "46",
            "--review-head-revision",
            "0123456789abcdef0123456789abcdef01234567",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads(output.read_text())
    assert evidence["schemaVersion"] == 2
    assert evidence["automatedReview"] == {
        "reviewer": "chatgpt-codex-connector[bot]",
        "status": "passed",
        "statusCheck": "ai/review",
        "headRevision": "0123456789abcdef0123456789abcdef01234567",
        "pullRequest": 46,
        "proof": "no-findings-reaction",
        "observedAt": "2026-07-26T20:35:51Z",
    }


def test_collector_rejects_unapproved_reviewer_receipt(tmp_path: Path) -> None:
    receipt = json.loads(
        (ROOT / "tests/contract/fixtures/gitops/valid-automated-review-evidence.json").read_text()
    )
    receipt["reviewer"] = "totally-unapproved-user"
    receipt_path = tmp_path / "review-receipt.json"
    receipt_path.write_text(json.dumps(receipt))
    result = subprocess.run(
        [
            str(ROOT / "scripts/ci/collect-argocd-evidence.sh"),
            "--release",
            str(ROOT / "tests/contract/fixtures/gitops/release-manifest.json"),
            "--automated-review-evidence",
            str(receipt_path),
            "--review-pull-request",
            "46",
            "--review-head-revision",
            "0123456789abcdef0123456789abcdef01234567",
            "--output",
            str(tmp_path / "evidence.json"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "not a valid successful gate receipt" in result.stderr


def test_collector_rejects_receipt_for_another_review_head(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            str(ROOT / "scripts/ci/collect-argocd-evidence.sh"),
            "--release",
            str(ROOT / "tests/contract/fixtures/gitops/release-manifest.json"),
            "--automated-review-evidence",
            str(ROOT / "tests/contract/fixtures/gitops/valid-automated-review-evidence.json"),
            "--review-pull-request",
            "46",
            "--review-head-revision",
            "abcdef0123456789abcdef0123456789abcdef01",
            "--output",
            str(tmp_path / "evidence.json"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "not a valid successful gate receipt" in result.stderr
