from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_container_and_aks_contract_exposes_expected_runtime_values():
    env_example = read_text(".env.example")
    deployment = read_text("deploy/k8s/base/deployment.yaml")
    service = read_text("deploy/k8s/base/service.yaml")
    overlay = read_text("deploy/k8s/overlays/aks-nonprod/kustomization.yaml")
    configmap = read_text("deploy/k8s/overlays/aks-nonprod/configmap.yaml")

    expected_keys = [
        "APP_NAME",
        "ENVIRONMENT",
        "DATABASE_URL",
        "LOG_LEVEL",
        "MAX_CLARIFYING_QUESTIONS",
        "ROADMAP_P95_SECONDS",
        "TOPIC_GUIDANCE_P95_SECONDS",
        "MAX_CONCURRENT_EMPLOYEES",
        "TOPIC_CATALOG_PATH",
    ]

    for key in expected_keys:
        assert f"{key}=" in env_example
        assert f"{key}:" in configmap

    assert "containerPort: 8000" in deployment
    assert "path: /health" in deployment
    assert "port: 80" in service
    assert "targetPort: http" in service
    assert "digest: sha256:REPLACE_WITH_IMMUTABLE_DIGEST" in overlay
    assert "sqlite:////app/devops-career-agent.db" in configmap


def test_deployment_contract_documents_rollback_history_and_restore_point():
    contract = read_text("specs/002-dockerize-deploy/contracts/deployment-contract.md")

    assert "rollout history" in contract
    assert "previous verified release" in contract
    assert "exact immutable image digest" in contract
