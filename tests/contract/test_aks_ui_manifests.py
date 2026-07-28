from __future__ import annotations

from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "deploy/k8s/base"
OVERLAY = ROOT / "deploy/k8s/overlays/aks-nonprod"
PLATFORM = ROOT / "deploy/k8s/platform/alb-controller"
INFRA = ROOT / "infra/azure"


def read(path: Path) -> str:
    return path.read_text()


def document(path: Path) -> dict[str, object]:
    return yaml.safe_load(read(path))


def test_pinned_alb_controller_precedes_gateway_and_legacy_ingress_is_absent() -> None:
    install = read(PLATFORM / "install-contract.yaml")
    digests = read(OVERLAY / "platform-digests.yaml")
    overlay = read(OVERLAY / "kustomization.yaml")
    assert "controller-ready-attestation" in install
    assert 'chartVersion: "1.11.1"' in install and 'gatewayApiCrdVersion: "v1.5.1"' in install
    assert "albControllerChart" in digests and "gatewayApiCrds" in digests
    order = "gateway-api-crds,alb-controller,controller-ready-attestation,gateway-resources"
    assert f"installOrder: {order}" in install
    assert "gateway.yaml" in overlay and "httproute.yaml" in overlay
    assert not (BASE / "ingress.yaml").exists()
    assert not list((ROOT / "deploy/k8s").rglob("*ingress*.yaml"))


def test_public_gateway_exposes_only_ui_and_bff_while_core_is_private_tls() -> None:
    route = read(OVERLAY / "httproute.yaml")
    gateway = read(OVERLAY / "gateway.yaml")
    private_service = document(OVERLAY / "private-machine-service.yaml")
    assert "certificateRefs" in gateway and "public-gateway-tls" in gateway
    assert "name: ui" in route and "name: bff" in route
    assert "name: core" not in route and "core-private-machine" not in route
    annotations = private_service["metadata"]["annotations"]
    assert annotations["service.beta.kubernetes.io/azure-load-balancer-internal"] == "true"
    assert private_service["spec"]["loadBalancerSourceRanges"] == ["${PRIVATE_MACHINE_SOURCE_CIDR}"]
    assert private_service["spec"]["ports"] == [{"name": "https", "port": 8443, "targetPort": "https"}]
    core = read(BASE / "core/deployment.yaml")
    assert "--ssl-certfile" in core and "--ssl-keyfile" in core
    assert "scheme: HTTPS" in core
    core_runtime = document(BASE / "core/configmap.yaml")["data"]
    assert "CORE_TLS_EXPECTED_SANS" in core_runtime


def test_every_replica_has_dependency_complete_readiness_and_csi_fail_closed() -> None:
    bff_config = document(BASE / "bff/configmap.yaml")["data"]
    core_config = document(BASE / "core/configmap.yaml")["data"]
    assert set(bff_config["READINESS_REQUIRED_DEPENDENCIES"].split(",")) == {
        "redis", "tenant-jwks", "session-key", "bff-client-certificate",
        "core-tls", "delegated-core-token", "health-app-token",
    }
    assert set(core_config["READINESS_REQUIRED_DEPENDENCIES"].split(",")) == {
        "postgresql", "tenant-jwks", "key-material", "tls-functional",
    }
    for service in ("bff", "core"):
        deployment = read(BASE / f"{service}/deployment.yaml")
        assert "replicas: 2" in deployment
        assert "readinessProbe:" in deployment
        assert "secrets-store.csi.k8s.io" in deployment
        assert "KEY_MATERIAL_FALLBACK, value: disabled" in deployment
    bff_config = document(BASE / "bff/configmap.yaml")["data"]
    core_config = document(BASE / "core/configmap.yaml")["data"]
    assert bff_config["BFF_CLIENT_CERTIFICATE_VERSION"] == "${BFF_CLIENT_CERTIFICATE_VERSION}"
    assert bff_config["CORE_CA_CERTIFICATE_VERSION"] == "${PRIVATE_CORE_CERTIFICATE_VERSION}"
    assert core_config["CORE_TLS_CERTIFICATE_VERSION"] == "${PRIVATE_CORE_CERTIFICATE_VERSION}"
    assert "JWKS_STALE_AFTER_SECONDS" in read(BASE / "bff/secret-provider-class.yaml") or "tenant-jwks" in bff_config["READINESS_REQUIRED_DEPENDENCIES"]


def test_ui_is_identityless_and_all_services_have_health_pdb_topology_hpa_and_digests() -> None:
    overlay = read(OVERLAY / "kustomization.yaml")
    assert re.search(r"digest: sha256:[0-9a-f]{64}", overlay)
    ui = read(BASE / "ui/deployment.yaml")
    assert "automountServiceAccountToken: false" in ui
    assert "azure.workload.identity/use" not in ui
    for service in ("ui", "bff", "core"):
        deployment = read(BASE / f"{service}/deployment.yaml")
        assert "livenessProbe:" in deployment and "readinessProbe:" in deployment
        assert "topologySpreadConstraints:" in deployment
        assert "kubernetes.io/hostname" in deployment
        assert "minReplicas: 2" in read(BASE / f"{service}/hpa.yaml")
        assert "maxReplicas: 4" in read(BASE / f"{service}/hpa.yaml")
        assert "maxUnavailable: 1" in read(BASE / f"{service}/pdb.yaml")


def test_runtime_images_expose_numeric_non_root_users() -> None:
    assert "USER 10001" in read(ROOT / "Dockerfile")
    assert "USER 1000" in read(ROOT / "bff/Dockerfile")
    assert "USER 101" in read(ROOT / "ui/Dockerfile")


def test_platform_bootstrap_restores_the_identityless_ui_service_account() -> None:
    bootstrap = read(ROOT / "scripts/azure/apply-career-agent-platform-runtime.sh")
    assert "deploy/k8s/base/ui/service-account.yaml" in bootstrap


def test_gateway_and_lab_jobs_have_exact_cadence_identity_and_network_confinement() -> None:
    gateway = read(BASE / "gateway-certificate-rotation/cronjob.yaml")
    lab = read(BASE / "lab-revalidation/cronjob.yaml")
    assert 'schedule: "17 */12 * * *"' in gateway
    assert "serviceAccountName: gateway-certificate-rotation" in gateway
    assert 'schedule: "13 */20 * * *"' in lab
    assert "serviceAccountName: lab-revalidation" in lab
    for path, client_id in (
        (BASE / "gateway-certificate-rotation/service-account.yaml", "GATEWAY_CERTIFICATE_DNS_CLIENT_ID"),
        (BASE / "lab-revalidation/service-account.yaml", "LAB_REVALIDATION_WORKLOAD_CLIENT_ID"),
    ):
        source = read(path)
        assert "azure.workload.identity/client-id" in source and client_id in source
    gateway_network = read(BASE / "gateway-certificate-rotation/network-policy.yaml")
    lab_network = read(BASE / "lab-revalidation/network-policy.yaml")
    assert "policyTypes: [Ingress, Egress]" in gateway_network
    assert "port: 443" in gateway_network
    assert "public-https-only" in lab_network and "port: 443" in lab_network
    for private in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16"):
        assert private in lab_network


def test_migration_and_hold_reconciler_are_separately_identity_bound_and_scheduled() -> None:
    migration = read(BASE / "migration/kustomization.yaml")
    admission = read(BASE / "migration/validating-admission-policy.yaml")
    hold = read(BASE / "evidence-hold-reconciler/cronjob.yaml")
    hold_sa = read(BASE / "evidence-hold-reconciler/service-account.yaml")
    assert "namespace.yaml" in migration
    assert "career-migrations" in read(BASE / "migration/namespace.yaml")
    assert "MIGRATION_CLIENT_ID" in read(BASE / "migration/service-account.yaml")
    assert "api://AzureADTokenExchange" in admission
    assert 'schedule: "0 * * * *"' in hold
    assert "reconcile-all" in hold and "EVIDENCE_HOLD_ROLE" in hold
    assert "EVIDENCE_HOLD_RECONCILER_CLIENT_ID" in hold_sa


def test_gateway_alb_and_kubelet_contracts_are_exact_and_mutually_denied() -> None:
    identities = read(INFRA / "identity.tf")
    alb = read(INFRA / "application-gateway-for-containers.tf")
    gateway = read(INFRA / "core-machine-certificate.tf")
    aks = read(INFRA / "main.tf")
    assert "exact-agc-resource-group-configuration" in identities and "exact-subnet-join" in identities
    for denied in ("aks-admin", "dns", "key-vault", "data-services", "unrelated-network"):
        assert denied in identities
    assert "AppGw for Containers Configuration Manager" in alb
    assert "Network Contributor" in alb
    for denied in ("private-key-export", "unrelated-certificate", "zone-destroy", "agc", "aks", "identity-admin", "data-services"):
        assert denied in identities
    assert "gateway_certificate_versions" in gateway and "gateway_named_dns_records" in gateway
    assert 'role_definition_name = "AcrPull"' in aks
    delivery = read(INFRA / "github-actions-identities.tf")
    for denied in ("acr-push-delete-import-admin", "role-assignment", "federation", "application-pod-assumption"):
        assert denied in delivery


def test_combined_alembic_release_has_one_deterministic_merge_head() -> None:
    merge = read(ROOT / "alembic/versions/009_merge_learning_progress.py")
    assert 'revision = "009_merge_learning_progress"' in merge
    assert 'down_revision = ("007_learning_sessions", "008_owned_progress")' in merge
    versions = list((ROOT / "alembic/versions").glob("*.py"))
    assert sum('revision = "009_merge_learning_progress"' in read(path) for path in versions) == 1
