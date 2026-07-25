from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_static_readiness_is_identityless_and_schema_shaped(tmp_path: Path) -> None:
    output = tmp_path / "readiness.json"
    result = subprocess.run(
        [str(ROOT / "scripts/ci/check-gitops-platform-ready.sh"), "--mode", "static", "--output", str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text())
    assert payload["status"] == "ready"
    assert payload["environment"] == "nonprod"
    assert payload["checks"]["registryPullSecret"]["name"] == "career-agent-acr-pull"
    assert set(payload["checks"]) == {"namespace", "argocdProject", "registryPullSecret", "registry", "workloadPrerequisites"}


def test_readiness_command_has_no_mutating_kubectl_operations() -> None:
    script = (ROOT / "scripts/ci/check-gitops-platform-ready.sh").read_text()
    assert "kubectl apply" not in script
    assert "kubectl create" not in script


def test_delivery_invokes_readiness_before_the_git_handoff() -> None:
    workflow = (ROOT / ".github/workflows/delivery.yml").read_text()
    assert "check-gitops-platform-ready.sh --mode static" in workflow
    assert "artifacts/release/readiness.json" in workflow
    assert "az aks get-credentials" not in workflow
