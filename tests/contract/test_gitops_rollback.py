from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_rollback_is_a_reviewed_git_reversion() -> None:
    workflow = (ROOT / ".github/workflows/rollback.yml").read_text()
    parsed = yaml.safe_load(workflow)
    script = (ROOT / "scripts/ci/prepare-gitops-rollback.sh").read_text()
    assert "create-pull-request" in workflow
    assert "verify-ai-review.sh" in workflow
    assert "AI_REVIEW_EVIDENCE_OUTPUT: artifacts/automated-review-evidence.json" in workflow
    assert "artifacts/automated-review-evidence.json" in workflow
    assert "pull-request-head-sha" in workflow
    assert 'verify-ai-review.sh "$GITHUB_REPOSITORY" "$PULL_REQUEST_NUMBER" "$EXPECTED_REVIEW_HEAD"' in workflow
    assert "rollback-review-scope.json" in workflow
    assert "statuses" not in parsed["permissions"]
    assert "statuses" not in parsed["jobs"]["prepare"]["permissions"]
    assert parsed["jobs"]["verify-rollback-review"]["permissions"]["statuses"] == "write"
    assert parsed["jobs"]["verify-rollback-review"]["permissions"]["contents"] == "write"
    assert "AI_REVIEW_MERGE: \"true\"" in workflow
    assert "Direct Argo CD rollback is not authoritative" in workflow
    assert "kubectl" not in workflow.lower()
    assert "terraform" not in workflow.lower()
    assert "approvalResult" in script
