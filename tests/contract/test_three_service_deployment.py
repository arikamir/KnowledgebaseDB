from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from api.routes.health import MountedPemMaterialProbe


ROOT = Path(__file__).resolve().parents[2]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text())


def test_public_gateway_routes_only_ui_and_bff_and_reserved_prefixes_to_fixed_ui_404():
    route = load("deploy/k8s/overlays/aks-nonprod/httproute.yaml")
    gateway = load("deploy/k8s/overlays/aks-nonprod/gateway.yaml")
    assert gateway["spec"]["gatewayClassName"] == "azure-alb-external"
    assert gateway["spec"]["listeners"][0]["protocol"] == "HTTPS"
    assert gateway["spec"]["listeners"][0]["tls"]["mode"] == "Terminate"
    backends = [ref["name"] for rule in route["spec"]["rules"] for ref in rule["backendRefs"]]
    assert set(backends) == {"ui", "bff"} and "core" not in backends
    reserved = route["spec"]["rules"][0]
    assert {match["path"]["value"] for match in reserved["matches"]} == {"/api/", "/internal/"}
    assert reserved["backendRefs"] == [{"name": "ui", "port": 80}]
    nginx = (ROOT / "ui/nginx.conf").read_text()
    assert "location ^~ /api/ { return 404; }" in nginx
    assert "location ^~ /internal/ { return 404; }" in nginx


def test_legacy_ingress_is_absent_and_aks_does_not_reenable_web_app_routing():
    base = load("deploy/k8s/base/kustomization.yaml")
    assert "ingress.yaml" not in base["resources"]
    assert not (ROOT / "deploy/k8s/base/ingress.yaml").exists()
    manifests = "\n".join(path.read_text() for path in (ROOT / "deploy/k8s").rglob("*.yaml"))
    assert "kind: Ingress\n" not in manifests
    assert "webapprouting.kubernetes.azure.com" not in manifests
    aks = (ROOT / "infra/azure/main.tf").read_text()
    assert "web_app_routing" not in aks


def test_core_is_https_only_on_cluster_and_internal_load_balancer_with_private_dns_and_sources():
    deployment = load("deploy/k8s/base/core/deployment.yaml")
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["ports"] == [{"name": "https", "containerPort": 8443}]
    assert container["args"][-4:] == [
        "--ssl-certfile", "/var/run/secrets/career-agent/core-tls.pem",
        "--ssl-keyfile", "/var/run/secrets/career-agent/core-tls.pem",
    ]
    for probe in (container["livenessProbe"], container["readinessProbe"]):
        assert probe["httpGet"]["scheme"] == "HTTPS" and probe["httpGet"]["port"] == "https"
    service = load("deploy/k8s/base/core/service.yaml")
    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"] == [{"name": "https", "port": 8443, "targetPort": "https"}]
    machine = load("deploy/k8s/overlays/aks-nonprod/private-machine-service.yaml")
    assert machine["metadata"]["annotations"]["service.beta.kubernetes.io/azure-load-balancer-internal"] == "true"
    assert machine["metadata"]["annotations"]["external-dns.alpha.kubernetes.io/hostname"] == "core.${PRIVATE_CORE_DNS_ZONE_NAME}"
    assert machine["spec"]["loadBalancerSourceRanges"] == ["${PRIVATE_MACHINE_SOURCE_CIDR}"]
    assert "loadBalancerIP" not in machine["spec"]


def test_core_and_bff_mount_exact_versioned_csi_material_without_plaintext_or_env_fallback():
    for service in ("core", "bff"):
        provider = load(f"deploy/k8s/base/{service}/secret-provider-class.yaml")
        parameters = provider["spec"]["parameters"]
        assert "objectVersion:" in parameters["objects"]
        assert "secretObjects" not in provider["spec"]
        deployment = load(f"deploy/k8s/base/{service}/deployment.yaml")
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        assert any(mount["readOnly"] for mount in container["volumeMounts"] if mount["name"] == "key-vault-material")
        env = {entry["name"]: entry["value"] for entry in container["env"]}
        assert env["KEY_MATERIAL_FALLBACK"] == "disabled"
        assert not any("PRIVATE_KEY" in name or "PASSWORD" in name for name in env)
    bff_config = load("deploy/k8s/base/bff/configmap.yaml")
    assert bff_config["data"]["CORE_BASE_URL"] == "https://core.career-agent.svc:8443/api/v1"


def test_three_services_have_independent_digest_images_and_bff_readiness_covers_redis_jwks_keys_and_trust():
    expected_images = {
        "ui": "${UI_IMAGE_REPOSITORY}@${UI_IMAGE_DIGEST}",
        "bff": "${BFF_IMAGE_REPOSITORY}@${BFF_IMAGE_DIGEST}",
        "core": "${CORE_IMAGE_REPOSITORY}@${CORE_IMAGE_DIGEST}",
    }
    for service, image in expected_images.items():
        deployment = load(f"deploy/k8s/base/{service}/deployment.yaml")
        assert deployment["spec"]["template"]["spec"]["containers"][0]["image"] == image
    required = set(load("deploy/k8s/base/bff/configmap.yaml")["data"]["READINESS_REQUIRED_DEPENDENCIES"].split(","))
    assert {"redis", "tenant-jwks", "session-key", "bff-client-certificate", "core-tls"} <= required
    health = (ROOT / "bff/src/routes/health.ts").read_text()
    assert "if (!(name in checks)) failed.push(name)" in health
    assert "if (!await check()) failed.push(name)" in health
    session_test = (ROOT / "bff/tests/integration/auth-session.test.ts").read_text()
    assert "does not clear a cookie when Redis state is indeterminate" in session_test
    assert 'expect(response.headers["set-cookie"]).toBeUndefined()' in session_test


def test_default_deny_and_exact_private_call_paths_are_declared():
    documents = list(yaml.safe_load_all((ROOT / "deploy/k8s/base/network-policies.yaml").read_text()))
    policies = {document["metadata"]["name"]: document for document in documents}
    assert policies["application-default-deny"]["spec"]["podSelector"] == {}
    assert policies["application-default-deny"]["spec"]["policyTypes"] == ["Ingress", "Egress"]
    core_ingress = policies["core-private-callers"]["spec"]["ingress"]
    assert core_ingress[0]["from"][0]["podSelector"]["matchLabels"]["app.kubernetes.io/name"] == "bff"
    assert core_ingress[1]["from"][0]["ipBlock"]["cidr"] == "${PRIVATE_MACHINE_SOURCE_CIDR}"
    lifecycle = policies["bff-browser-and-lifecycle"]["spec"]["ingress"][1]
    assert lifecycle["from"][0]["podSelector"]["matchLabels"]["app.kubernetes.io/name"] == "lifecycle-revocation-dispatcher"


def test_source_range_nsg_and_machine_app_role_form_defense_in_depth():
    machine = load("deploy/k8s/overlays/aks-nonprod/private-machine-service.yaml")
    assert machine["spec"]["loadBalancerSourceRanges"] == ["${PRIVATE_MACHINE_SOURCE_CIDR}"]
    agc = (ROOT / "infra/azure/application-gateway-for-containers.tf").read_text()
    assert 'resource "azurerm_network_security_group" "application_gateway_for_containers"' in agc
    assert "source_address_prefixes    = var.browser_gateway_source_cidrs" in agc
    machines = (ROOT / "infra/azure/entra-machine-registrations.tf").read_text()
    assert 'type = "Role"' in machines
    assert "app_role_assignment_required = true" in machines
    assert "app_role_ids[each.value.role]" in machines
    authz = (ROOT / "src/api/routes/authz.py").read_text()
    assert "machine_principal" in authz and "validate_machine_token" in authz


@pytest.mark.parametrize("failed", ["postgresql", "tenant-jwks", "key-material", "tls-functional"])
def test_core_dependency_failure_is_replica_local_while_process_liveness_stays_up(app, client, monkeypatch, failed):
    dependencies = ("postgresql", "tenant-jwks", "key-material", "tls-functional")
    monkeypatch.setenv("READINESS_REQUIRED_DEPENDENCIES", ",".join(dependencies))
    app.state.readiness_checks = {name: (lambda ready=name != failed: ready) for name in dependencies}
    ready = client.get("/health/ready")
    assert ready.status_code == 503 and ready.json()["failedDependencies"] == [failed]
    assert client.get("/health/live").status_code == 200


def pem_material(tmp_path: Path, *, expired=False, mismatched=False) -> Path:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    certificate_key = rsa.generate_private_key(public_exponent=65537, key_size=2048) if mismatched else key
    now = datetime.now(timezone.utc)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Career Agent Private CA")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer).public_key(certificate_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(now - timedelta(days=1) if expired else now + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("core.career-agent.svc")]), critical=False)
        .sign(certificate_key, hashes.SHA256())
    )
    path = tmp_path / "core.pem"
    path.write_bytes(
        certificate.public_bytes(serialization.Encoding.PEM)
        + key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    return path


@pytest.mark.parametrize("case", ["missing", "mismatched", "expired"])
def test_core_certificate_probe_fails_closed_for_each_replica_material_fault(tmp_path, case):
    path = tmp_path / "missing.pem" if case == "missing" else pem_material(
        tmp_path, expired=case == "expired", mismatched=case == "mismatched",
    )
    probe = MountedPemMaterialProbe(path, "version-1", frozenset({"core.career-agent.svc"}), "Career Agent Private CA")
    try:
        ready = probe()
    except Exception:
        ready = False
    assert ready is False
