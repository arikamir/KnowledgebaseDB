from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_delivery_opens_a_bot_pr_and_requires_copilot_before_main() -> None:
    workflow = (ROOT / ".github/workflows/delivery.yml").read_text()
    assert "peter-evans/create-pull-request" in workflow
    assert "automation/gitops-release-" in workflow
    assert "scripts/ci/verify-copilot-review.sh" in workflow
    assert "protected `main`" in workflow
    assert "branch: main" not in workflow


def test_copilot_gate_is_status_check_based_and_fails_closed() -> None:
    script = (ROOT / "scripts/ci/verify-copilot-review.sh").read_text()
    assert "copilot-pull-request-reviewer[bot]" in script
    assert "requested_reviewers" in script
    assert "pulls/$pull_request/reviews" in script
    assert '.commit_id == $head' in script
    assert "statuses/$head_sha" in script
    assert "required Copilot review is missing or stale" in script
