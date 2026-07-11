from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_rollback_flow_is_documented_end_to_end():
    quickstart = read_text("specs/002-dockerize-deploy/quickstart.md")
    contract = read_text("specs/002-dockerize-deploy/contracts/deployment-contract.md")

    assert "kubectl rollout undo deployment/devops-career-agent -n devops-career-agent" in quickstart
    assert "kubectl rollout status deployment/devops-career-agent -n devops-career-agent" in quickstart
    assert "Verify `/health` again" in quickstart
    assert "Rollback restores the previous verified release" in contract
