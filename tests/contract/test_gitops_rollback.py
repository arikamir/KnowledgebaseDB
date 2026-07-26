from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_rollback_is_a_reviewed_git_reversion() -> None:
    workflow = (ROOT / ".github/workflows/rollback.yml").read_text()
    script = (ROOT / "scripts/ci/prepare-gitops-rollback.sh").read_text()
    assert "create-pull-request" in workflow
    assert "verify-ai-review.sh" in workflow
    assert "Direct Argo CD rollback is not authoritative" in workflow
    assert "kubectl" not in workflow.lower()
    assert "terraform" not in workflow.lower()
    assert "approvalResult" in script
