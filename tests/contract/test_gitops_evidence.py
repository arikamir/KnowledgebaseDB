from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_evidence_schema_is_closed_and_redaction_aware() -> None:
    schema = json.loads((ROOT / "config/gitops-evidence.schema.json").read_text())
    assert schema["$id"].endswith("gitops-evidence-v3.json")
    assert schema["properties"]["schemaVersion"] == {"const": 3}
    assert schema["additionalProperties"] is False
    assert "automatedReview" in schema["required"]
    assert "timing" in schema["required"]
    assert "migration" in schema["required"]


def test_collector_requires_release_and_contains_audit_fields() -> None:
    script = (ROOT / "scripts/ci/collect-argocd-evidence.sh").read_text()
    assert "schemaVersion:3" in script
    assert "--automated-review-evidence must be a receipt produced by the current-head gate" in script
    assert "--automated-reviewer" not in script
    assert "--automated-review-status" not in script
    assert '"approved-review"' in script
    assert '"no-findings-reaction"' in script
    assert '"no-findings-comment"' in script
    assert "proofCommentId" in script
    assert 'commits/$EXPECTED_REVIEW_HEAD/status' in script
    assert 'issues/comments/$AUTOMATED_REVIEW_COMMENT_ID/reactions' in script
    assert 'issues/$EXPECTED_REVIEW_PR/reactions' in script
    assert "reactions?per_page=100" in script
    assert "credential-shaped content is forbidden" in script
    assert "humanAction" in script
    assert "rollback" in script
    assert "GITOPS_AFFECTED_SERVICE" in script
    assert "--migration-job must identify the retained Argo migration Job" in script
    assert "migration Job does not match the release source revision" in script
    assert "migration did not reach the approved target" in script
    assert "kubectl delete" not in script


def test_collector_consumes_successful_gate_receipt(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env bash
case "$*" in
  *"pulls/46 --jq .head.sha"*) printf '%s\\n' '0123456789abcdef0123456789abcdef01234567' ;;
  *"commits/0123456789abcdef0123456789abcdef01234567/status"*) printf '%s\\n' 'success' ;;
  *"issues/comments/5085272253 --jq .body"*) printf '%s\\n\\n%s\\n' '@codex review' '<!-- ai-review-head:0123456789abcdef0123456789abcdef01234567 -->' ;;
  *"issues/comments/5085272253/reactions"*) printf '%s\\n' '[[{"content":"+1","user":{"login":"chatgpt-codex-connector[bot]"}}]]' ;;
  *) exit 1 ;;
esac
"""
    )
    fake_gh.chmod(0o755)
    fake_kubectl = fake_bin / "kubectl"
    fake_kubectl.write_text(
        """#!/usr/bin/env bash
case "$*" in
  *"get job core-migration-0123456789ab -o json"*) printf '%s\\n' '{"metadata":{"name":"core-migration-0123456789ab","namespace":"career-migrations","annotations":{"argocd.argoproj.io/hook":"PreSync"}},"status":{"conditions":[{"type":"Complete","status":"True"}]},"spec":{"template":{"spec":{"containers":[{"name":"core-migration","image":"acrdevopscareeruaenonprod.azurecr.io/core@sha256:2222222222222222222222222222222222222222222222222222222222222222","env":[{"name":"MIGRATION_TARGET","value":"009_merge_learning_progress"}]}]}}}}' ;;
  *"logs job/core-migration-0123456789ab -c core-migration"*) printf '%s\\n' 'MIGRATION_BEFORE_HEADS=007_learning_sessions,008_owned_progress' 'MIGRATION_AFTER_HEADS=009_merge_learning_progress' ;;
  *) exit 1 ;;
esac
"""
    )
    fake_kubectl.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
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
            "--migration-job",
            "core-migration-0123456789ab",
            "--migration-log-output",
            str(tmp_path / "migration.log"),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads(output.read_text())
    assert evidence["schemaVersion"] == 3
    assert evidence["automatedReview"] == {
        "reviewer": "chatgpt-codex-connector[bot]",
        "status": "passed",
        "statusCheck": "ai/review",
        "headRevision": "0123456789abcdef0123456789abcdef01234567",
        "pullRequest": 46,
        "proof": "no-findings-reaction",
        "observedAt": "2026-07-26T20:35:51Z",
    }
    assert evidence["migration"]["jobName"] == "core-migration-0123456789ab"
    assert evidence["migration"]["status"] == "succeeded"
    assert evidence["migration"]["beforeHeads"] == [
        "007_learning_sessions",
        "008_owned_progress",
    ]
    assert evidence["migration"]["afterHeads"] == ["009_merge_learning_progress"]
    assert len(evidence["migration"]["logs"]["sha256"]) == 64


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
            "--migration-job",
            "core-migration-test-42",
            "--migration-log-output",
            str(tmp_path / "migration.log"),
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
            "--migration-job",
            "core-migration-test-42",
            "--migration-log-output",
            str(tmp_path / "migration.log"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "not a valid successful gate receipt" in result.stderr
