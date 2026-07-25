from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_release_workflow_and_application_manifests_remain_least_privilege() -> None:
    workflow = (ROOT / ".github/workflows/delivery.yml").read_text().lower()
    assert "id-token: write" in workflow
    assert "contents: write" in workflow
    assert "aks get-credentials" not in workflow
    assert "terraform" not in workflow
    assert "promote.sh" not in workflow
    for path in (ROOT / "deploy/argocd").rglob("*.yaml"):
        text = path.read_text().lower()
        assert "clientsecret:" not in text
        assert "kubeconfig" not in text


def test_argocd_application_set_has_no_platform_paths() -> None:
    text = (ROOT / "deploy/argocd/applicationset.yaml").read_text().lower()
    assert "infra/" not in text
    assert "gateway" not in text
    assert "namespace.yaml" not in text
