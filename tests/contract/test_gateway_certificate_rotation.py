from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "deploy/k8s/base/gateway-certificate-rotation"


def test_public_gateway_rotation_has_the_complete_normal_partial_rollback_and_emergency_contract():
    script = (ROOT / "scripts/azure/rotate-gateway-certificate.sh").read_text()
    for action in ("stage", "activate", "converge", "retire", "rollback", "emergency"):
        assert f"  {action})" in script
    assert 'if [[ "$ACTION" == scheduled ]]' in script
    assert "elapsed >= 86400 && elapsed <= 172800" in script
    assert "retryUntil" in script and "quarantined" in script and "pageRequired" in script
    assert "--subresource=status" in script and "CertificateConverged" in script
    assert "safeFallbackAllowed=false" in script
    assert "retiredVersions" in script and "disable_version" in script
    for prohibited in ("employee_id", "roadmap", "progress", "DATABASE_URL"):
        assert prohibited not in script


def test_rotation_cron_is_twelve_hour_bounded_digest_pinned_and_exact_identity_network_scoped():
    cron = yaml.safe_load((MANIFESTS / "cronjob.yaml").read_text())
    assert cron["spec"]["schedule"] == "17 */12 * * *"
    assert cron["spec"]["concurrencyPolicy"] == "Forbid"
    job = cron["spec"]["jobTemplate"]["spec"]
    assert job["activeDeadlineSeconds"] == 1800
    container = job["template"]["spec"]["containers"][0]
    assert "@${GATEWAY_CERTIFICATE_ROTATION_IMAGE_DIGEST}" in container["image"]
    account = yaml.safe_load((MANIFESTS / "service-account.yaml").read_text())
    assert account["metadata"]["annotations"]["azure.workload.identity/client-id"] == "${GATEWAY_CERTIFICATE_DNS_CLIENT_ID}"
    policy = yaml.safe_load((MANIFESTS / "network-policy.yaml").read_text())["spec"]
    assert policy["policyTypes"] == ["Ingress", "Egress"] and policy["ingress"] == []
    assert (ROOT / "config/operational-alert-profile-v1.yaml").exists()
