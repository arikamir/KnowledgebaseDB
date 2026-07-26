from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_delivery_opens_a_bot_pr_and_requires_automated_review_before_main() -> None:
    workflow = (ROOT / ".github/workflows/delivery.yml").read_text()
    assert "peter-evans/create-pull-request" in workflow
    assert "automation/gitops-release-" in workflow
    assert "scripts/ci/verify-ai-review.sh" in workflow
    assert "protected `main`" in workflow
    assert "branch: main" not in workflow


def test_automated_review_gate_is_status_based_and_fails_closed() -> None:
    script = (ROOT / "scripts/ci/verify-ai-review.sh").read_text()
    assert "chatgpt-codex-connector[bot]" in script
    assert "AI_REVIEW_APPROVED_LOGINS" in script
    assert "pulls/$pull_request/reviews" in script
    assert "--paginate --slurp" in script
    assert "per_page=100" in script
    assert '.commit_id == $head' in script
    assert "statuses/$head_sha" in script
    assert "required automated review is missing or stale" in script
