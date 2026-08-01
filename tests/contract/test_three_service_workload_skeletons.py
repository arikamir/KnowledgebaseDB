from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "deploy/k8s/base"


def document(path: str) -> dict:
    return yaml.safe_load((BASE / path).read_text())


def test_ui_bff_and_core_are_independent_digest_pinned_workloads_and_services() -> None:
    for name, port in (("ui", 8080), ("bff", 3000), ("core", 8443)):
        deployment = document(f"{name}/deployment.yaml")
        service = document(f"{name}/service.yaml")
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        assert deployment["metadata"]["name"] == name
        assert service["metadata"]["name"] == name
        assert service["spec"]["type"] == "ClusterIP"
        assert container["name"] == name
        assert "@${" in container["image"] and container["image"].endswith("_DIGEST}")
        assert container["ports"][0]["containerPort"] == port
        assert container["livenessProbe"]["httpGet"]["path"] == "/health/live"
        assert container["readinessProbe"]["httpGet"]["path"] == "/health/ready"
        assert container["securityContext"]["readOnlyRootFilesystem"] is True
    root = document("kustomization.yaml")["resources"]
    for name in ("ui", "bff", "core", "lifecycle", "retention"):
        assert name in root
    assert "deployment.yaml" not in root and "service.yaml" not in root


def test_backends_enforce_numeric_non_root_runtime_identities() -> None:
    for name, runtime_id in (("bff", 1000), ("core", 10001)):
        deployment = document(f"{name}/deployment.yaml")
        pod = deployment["spec"]["template"]["spec"]
        container_security = pod["containers"][0]["securityContext"]
        assert pod["securityContext"]["runAsNonRoot"] is True
        assert container_security["runAsUser"] == runtime_id
        assert container_security["runAsGroup"] == runtime_id


def test_dependency_readiness_is_replica_local_and_service_selector_driven() -> None:
    for name, dependencies in {
        "bff": ("redis", "tenant-jwks", "session-key", "bff-client-certificate", "core-tls"),
        "core": ("postgresql", "tenant-jwks", "key-material"),
    }.items():
        deployment = document(f"{name}/deployment.yaml")
        service = document(f"{name}/service.yaml")
        config = (BASE / f"{name}/configmap.yaml").read_text()
        labels = deployment["spec"]["template"]["metadata"]["labels"]
        assert service["spec"]["selector"]["app.kubernetes.io/name"] == name
        assert labels["app.kubernetes.io/name"] == name
        assert deployment["spec"]["replicas"] >= 2
        for dependency in dependencies:
            assert dependency in config


def test_static_ui_requires_runtime_config_and_rejects_reserved_core_prefixes() -> None:
    deployment = document("ui/deployment.yaml")
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert "runtime-config.json" in str(container["startupProbe"])
    runtime = document("ui/runtime-config.yaml")
    assert runtime["data"]["runtime-config.json"]
    nginx = (ROOT / "ui/nginx.conf").read_text()
    assert "try_files /runtime-config.json =503" in nginx
    assert "location ^~ /api/ { return 404; }" in nginx
    assert "location ^~ /internal/ { return 404; }" in nginx


def test_lifecycle_and_retention_jobs_use_dedicated_identities_and_bounded_cadences() -> None:
    reconcile = document("lifecycle/reconciliation-cronjob.yaml")
    dispatch = document("lifecycle/revocation-dispatch-cronjob.yaml")
    retention = document("retention/cronjob.yaml")
    assert reconcile["spec"]["schedule"] == "17 */4 * * *"
    assert dispatch["spec"]["schedule"] == "*/5 * * * *"
    assert retention["spec"]["schedule"] == "23 * * * *"
    for job, account in ((reconcile, "lifecycle"), (dispatch, "lifecycle"), (retention, "retention")):
        assert job["spec"]["concurrencyPolicy"] == "Forbid"
        spec = job["spec"]["jobTemplate"]["spec"]
        assert spec["activeDeadlineSeconds"] <= 1800
        pod = spec["template"]["spec"]
        assert pod["serviceAccountName"] == account
        assert "@${CORE_IMAGE_DIGEST}" in pod["containers"][0]["image"]
        assert pod["containers"][0]["securityContext"]["readOnlyRootFilesystem"] is True
    assert "LIFECYCLE_WORKLOAD_CLIENT_ID" in (BASE / "lifecycle/service-account.yaml").read_text()
    assert "RETENTION_WORKLOAD_CLIENT_ID" in (BASE / "retention/service-account.yaml").read_text()


def test_migration_resources_remain_separate_and_unmodified_by_workload_base() -> None:
    root = document("kustomization.yaml")["resources"]
    assert "migration" not in root
    assert (BASE / "migration/job-template.yaml").exists()
    for name in ("ui", "bff", "core", "lifecycle", "retention"):
        text = "\n".join(path.read_text() for path in (BASE / name).glob("*.yaml"))
        assert "run-core-migration" not in text
