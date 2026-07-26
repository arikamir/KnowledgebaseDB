from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_delivery_opens_a_bot_pr_and_requires_automated_review_before_main() -> None:
    workflow = (ROOT / ".github/workflows/delivery.yml").read_text()
    parsed = yaml.safe_load(workflow)
    assert "peter-evans/create-pull-request" in workflow
    assert "automation/gitops-release-" in workflow
    assert "scripts/ci/verify-ai-review.sh" in workflow
    assert "AI_REVIEW_EVIDENCE_OUTPUT: artifacts/automated-review-evidence.json" in workflow
    assert "artifacts/automated-review-evidence.json" in workflow
    assert "pull-request-head-sha" in workflow
    assert "protected `main`" in workflow
    assert "branch: main" not in workflow
    assert "statuses" not in parsed["permissions"]
    assert "statuses" not in parsed["jobs"]["open-release-pr"]["permissions"]
    assert parsed["jobs"]["verify-release-review"]["permissions"]["statuses"] == "write"
    assert parsed["jobs"]["verify-release-review"]["permissions"]["contents"] == "write"
    assert parsed["jobs"]["verify-release-review"]["needs"] == "open-release-pr"
    assert "AI_REVIEW_MERGE: \"true\"" in workflow


def test_automated_review_gate_is_status_based_and_fails_closed() -> None:
    script = (ROOT / "scripts/ci/verify-ai-review.sh").read_text()
    assert "chatgpt-codex-connector[bot]" in script
    assert "AI_REVIEW_APPROVED_LOGINS" in script
    assert "pulls/$pull_request/reviews" in script
    assert "--paginate --slurp" in script
    assert "per_page=100" in script
    assert '.commit_id == $head' in script
    assert "ai-review-head:$head_sha" in script
    assert "review_request_id=" in script
    assert "AI_REVIEW_REQUESTER_LOGIN" in script
    assert ".body == $body and .user.login == $requester" in script
    assert "candidate_request_id/reactions" in script
    assert "completed_reviewer" in script
    assert "AI_REVIEW_EVIDENCE_OUTPUT" in script
    assert "write_review_evidence" in script
    assert "require_unchanged_head" in script
    assert "merge_verified_pull_request" in script
    assert "automated review changed before protected merge" in script
    assert "head changed during automated review" in script
    assert "issues/$pull_request/comments" in script
    assert 'content == "+1"' in script
    assert '"APPROVED"' in script
    assert '"CHANGES_REQUESTED"' in script
    assert '"DISMISSED"' in script
    assert "reported findings for current PR head" in script
    assert "statuses/$head_sha" in script
    assert "required automated review is missing or stale" in script
