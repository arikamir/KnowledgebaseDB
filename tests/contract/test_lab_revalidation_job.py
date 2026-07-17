from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "deploy/k8s/base/lab-revalidation"


def load(name): return yaml.safe_load((BASE / name).read_text())


def test_revalidation_job_is_bounded_nonoverlapping_identity_scoped_and_runs_within_twenty_hours():
    cron = load("cronjob.yaml")
    assert cron["spec"]["schedule"] == "13 */20 * * *"
    assert cron["spec"]["concurrencyPolicy"] == "Forbid"
    job = cron["spec"]["jobTemplate"]["spec"]
    assert job["activeDeadlineSeconds"] == 3600 and job["backoffLimit"] == 2
    pod = job["template"]["spec"]
    assert pod["serviceAccountName"] == "lab-revalidation"
    assert "@${CORE_IMAGE_DIGEST}" in pod["containers"][0]["image"]
    account = load("service-account.yaml")
    assert account["metadata"]["annotations"]["azure.workload.identity/client-id"] == "${LAB_REVALIDATION_WORKLOAD_CLIENT_ID}"


def test_network_policy_is_default_deny_with_public_https_and_exact_private_dependencies_only():
    policy = load("network-policy.yaml")["spec"]
    assert policy["policyTypes"] == ["Ingress", "Egress"] and policy["ingress"] == []
    public = policy["egress"][0]
    assert public["ports"] == [{"protocol": "TCP", "port": 443}]
    excluded = set(public["to"][0]["ipBlock"]["except"])
    assert {"10.0.0.0/8", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12", "192.168.0.0/16"} <= excluded
    contract = (ROOT / "infra/azure/data-plane-rbac.tf").read_text()
    assert 'lab-validation = {' in contract
    assert "employee-profile" in contract and "learning-session" in contract and "content-publish" in contract
