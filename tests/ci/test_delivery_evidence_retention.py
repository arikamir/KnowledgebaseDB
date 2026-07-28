from __future__ import annotations

from pathlib import Path
import json
import os
import re
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
TERRAFORM = ROOT / "infra/azure/delivery-evidence-storage.tf"
MANAGER = ROOT / "scripts/ci/manage-evidence-hold.sh"
RECONCILER = ROOT / "deploy/k8s/base/evidence-hold-reconciler"
AUTHORIZATION = ROOT / "infra/azure/delivery-evidence-hold-managers.tf"
VALIDATE_EVIDENCE = ROOT / "scripts/ci/validate-evidence.sh"


def source() -> str:
    return TERRAFORM.read_text()


def block(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_evidence_versions_receive_a_fixed_locked_ninety_day_policy() -> None:
    text = source()
    evidence = block(
        text,
        'resource "azurerm_storage_account" "delivery_evidence"',
        'resource "azurerm_storage_container" "delivery_evidence"',
    )
    assert "versioning_enabled  = true" in evidence
    assert "change_feed_enabled = true" in evidence
    assert "period_since_creation_in_days = 90" in evidence
    assert "state = var.delivery_evidence_policy_state" in evidence
    assert "allow_protected_append_writes = false" in evidence


def test_lifecycle_attempts_deletion_only_after_the_base_lock() -> None:
    text = source()
    policy = block(
        text,
        'resource "azurerm_storage_management_policy" "delivery_evidence"',
        'resource "azurerm_storage_account" "evidence_hold_control"',
    )
    assert policy.count("delete_after_days_since_creation") == 2
    assert policy.count("= 90") >= 2
    assert 'prefix_match = ["deliveries/"]' in policy
    assert "Azure skips deletion" in text
    assert "version-level legal hold remains" in text
    assert "immutable_until" in text


def test_hold_inventory_and_audit_are_separate_from_evidence_content() -> None:
    text = source()
    assert 'resource "azurerm_storage_account" "delivery_evidence"' in text
    assert 'resource "azurerm_storage_account" "evidence_hold_control"' in text
    assert 'name                  = "hold-inventory"' in text
    assert 'name                  = "hold-audit"' in text
    assert "storage_account_id    = azurerm_storage_account.evidence_hold_control.id" in text
    hold_account = block(
        text,
        'resource "azurerm_storage_account" "evidence_hold_control"',
        'resource "azurerm_storage_container" "evidence_hold_inventory"',
    )
    assert "immutability_policy" not in hold_account
    assert "shared_access_key_enabled       = false" in hold_account
    assert "public_network_access_enabled   = false" in hold_account


def test_hold_audit_is_append_only_but_cannot_change_the_evidence_lock() -> None:
    text = source()
    audit_policy = block(
        text,
        'resource "azurerm_storage_container_immutability_policy" "evidence_hold_audit"',
        'resource "azurerm_storage_management_policy" "evidence_hold_control"',
    )
    assert re.search(r"immutability_period_in_days\s*=\s*180", audit_policy)
    assert re.search(r"locked\s*=\s*true", audit_policy)
    assert re.search(r"protected_append_writes_enabled\s*=\s*true", audit_policy)
    assert "delivery_evidence" not in audit_policy

    control_lifecycle = block(
        text,
        'resource "azurerm_storage_management_policy" "evidence_hold_control"',
        'output "delivery_evidence_storage_account_id"',
    )
    assert 'prefix_match = ["hold-inventory/", "hold-audit/"]' in control_lifecycle
    assert "delete_after_days_since_creation_greater_than = 180" in control_lifecycle


def test_storage_surfaces_are_private_versioned_and_keyless() -> None:
    text = source()
    assert text.count("shared_access_key_enabled       = false") == 2
    assert text.count("public_network_access_enabled   = false") == 2
    assert text.count("allow_nested_items_to_be_public = false") == 2
    assert len(re.findall(r'min_tls_version\s*=\s*"TLS1_2"', text)) == 2
    assert text.count("versioning_enabled  = true") == 2


def test_writer_reader_manager_and_reconciler_authority_is_separated() -> None:
    storage = source()
    authorization = AUTHORIZATION.read_text()
    writer = block(
        storage,
        'resource "azurerm_role_definition" "delivery_evidence_exact_writer"',
        'resource "azurerm_role_assignment" "publisher_evidence_prefix"',
    )
    assert "blobs/delete" in writer
    assert "containers/setLegalHold/action" in writer
    assert "containers/clearLegalHold/action" in writer
    assert "containers/immutabilityPolicies/*" in writer
    assert "listKeys/action" in writer
    assert "blobs/list" not in writer
    assert "publisher_evidence_condition" in storage
    assert "Storage Blob Data Reader" in storage

    manager = block(
        authorization,
        'resource "azurerm_role_definition" "evidence_hold_manager_control"',
        'resource "azurerm_role_assignment" "evidence_hold_manager_inventory"',
    )
    reconciler = block(
        authorization,
        'resource "azurerm_role_definition" "evidence_version_hold_reconciler"',
        'resource "azurerm_role_assignment" "evidence_hold_reconciler_versions"',
    )
    assert "delivery-evidence itself" in authorization
    assert "containers/setLegalHold/action" in manager
    assert "containers/clearLegalHold/action" in manager
    assert "immutabilityPolicies/*" in manager
    assert "data_actions = []" in reconciler
    for denied in ("blobs/read", "blobs/write", "blobs/delete", "blobs/tags/write"):
        assert denied in reconciler
    assert "azurerm_storage_container.delivery_evidence.id" in authorization
    assert "evidence_hold_audit" not in reconciler


def test_authorization_contract_records_cross_prefix_and_cross_role_denials() -> None:
    authorization = AUTHORIZATION.read_text()
    for required in (
        "hold-request-create-extend-release", "hold-audit-append-read",
        "delivery-blob-content", "direct-version-hold", "fixed-policy-mutation",
        "hold-inventory-read", "enumerated-version-hold-set-clear",
        "delivery-blob-content-read-list-delete", "delivery-evidence-write",
        "hold-request-write", "hold-audit-access",
    ):
        assert required in authorization
    storage = source()
    assert "deliveries/${var.environment}/*/${stage}/*" in storage
    assert "environment-prefix-evidence" in (ROOT / "infra/azure/github-actions-identities.tf").read_text()


def inventory(tmp_path: Path) -> Path:
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps({
        "schemaVersion": 1,
        "evidenceSetId": "nonprod/build-42",
        "inventoryComplete": True,
        "expectedVersionCount": 2,
        "storageAccount": "stevidence0001",
        "container": "delivery-evidence",
        "versions": [
            {"blob": "deliveries/nonprod/build-42/pre/plan.json", "versionId": "2026-07-17T00:00:00Z", "immutableUntil": "2026-10-15T00:00:00Z"},
            {"blob": "deliveries/nonprod/build-42/post/result.json", "versionId": "2026-07-17T00:01:00Z", "immutableUntil": "2026-10-15T00:01:00Z"},
        ],
    }))
    return path


def run_manager(
    tmp_path: Path, *args: str, role: str = "manager", now: str = "2026-07-17T12:00:00Z",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(MANAGER), *args, "--state-dir", str(tmp_path / "state"),
         "--audit-dir", str(tmp_path / "audit"), "--now", now],
        cwd=ROOT, env=os.environ | {"EVIDENCE_HOLD_ROLE": role}, text=True, capture_output=True,
    )


def test_manager_validates_complete_exact_version_inventory_and_180_day_ceiling(tmp_path: Path) -> None:
    created = run_manager(
        tmp_path, "create", "--inventory", str(inventory(tmp_path)), "--hold-id", "incident-42",
        "--owner", "platform-operator-1", "--reason", "incident investigation",
        "--incident", "INC-42", "--expires-at", "2026-12-01T12:00:00Z",
    )
    assert created.returncode == 0, created.stderr
    state = json.loads((tmp_path / "state/incident-42.json").read_text())
    assert state["status"] == "applying"
    assert len(state["versions"]) == state["expectedVersionCount"] == 2
    assert all(item["desiredHold"] is True for item in state["versions"])
    assert list((tmp_path / "audit").glob("*.jsonl"))

    rejected = run_manager(
        tmp_path, "create", "--inventory", str(inventory(tmp_path)), "--hold-id", "too-long",
        "--owner", "platform-operator-1", "--reason", "incident investigation",
        "--incident", "INC-43", "--expires-at", "2027-02-01T12:00:00Z",
    )
    assert rejected.returncode != 0
    assert not (tmp_path / "state/too-long.json").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(inventoryComplete=False),
        lambda value: value.update(expectedVersionCount=3),
        lambda value: value["versions"].append(dict(value["versions"][0])),
        lambda value: value["versions"][0].update(blob="other-prefix/nonprod/build-42/plan.json"),
        lambda value: value["versions"][0].update(immutableUntil="not-a-date"),
        lambda value: value.update(container="cross-environment-evidence"),
    ],
)
def test_malformed_incomplete_cross_prefix_inventory_fails_without_state_or_audit(
    tmp_path: Path, mutation,
) -> None:
    payload = json.loads(inventory(tmp_path).read_text())
    mutation(payload)
    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps(payload))
    result = run_manager(
        tmp_path, "create", "--inventory", str(malformed), "--hold-id", "incident-42",
        "--owner", "platform-operator-1", "--reason", "incident investigation",
        "--incident", "INC-42", "--expires-at", "2026-12-01T12:00:00Z",
    )
    assert result.returncode != 0
    assert not (tmp_path / "state/incident-42.json").exists()
    assert not list((tmp_path / "audit").glob("*.jsonl"))


def test_only_manager_requests_changes_and_only_reconciler_touches_azure(tmp_path: Path) -> None:
    inv = inventory(tmp_path)
    denied = run_manager(tmp_path, "create", "--inventory", str(inv), "--hold-id", "denied", role="reconciler")
    assert denied.returncode != 0
    source = MANAGER.read_text()
    assert "az rest" in source
    assert "az storage blob download" not in source
    assert "az storage blob list" not in source
    assert "immutability-policy" not in source
    assert "EVIDENCE_HOLD_ROLE" in source


@pytest.mark.parametrize(("action", "role"), [("extend", "writer"), ("release", "reader"), ("reconcile-all", "manager")])
def test_unauthorized_hold_actions_fail_closed(tmp_path: Path, action: str, role: str) -> None:
    create_hold(tmp_path)
    args = [action]
    if action != "reconcile-all":
        args += ["--hold-id", "incident-42"]
    if action == "extend":
        args += ["--expires-at", "2026-12-15T12:00:00Z"]
    result = run_manager(tmp_path, *args, role=role)
    assert result.returncode != 0


def create_hold(tmp_path: Path, hold_id: str = "incident-42") -> None:
    result = run_manager(
        tmp_path, "create", "--inventory", str(inventory(tmp_path)), "--hold-id", hold_id,
        "--owner", "platform-operator-1", "--reason", "incident investigation",
        "--incident", "INC-42", "--expires-at", "2026-12-01T12:00:00Z",
    )
    assert result.returncode == 0, result.stderr


def fake_az(tmp_path: Path, failing_version: str = "") -> dict[str, str]:
    binary = tmp_path / "bin"
    binary.mkdir(exist_ok=True)
    az = binary / "az"
    az.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$AZ_LOG\"\n"
        "[[ -z \"${FAIL_VERSION:-}\" || \"$*\" != *\"$FAIL_VERSION\"* ]]\n"
    )
    az.chmod(0o755)
    return os.environ | {
        "PATH": f"{binary}:{os.environ['PATH']}",
        "AZ_LOG": str(tmp_path / "az.log"),
        "FAIL_VERSION": failing_version,
        "EVIDENCE_HOLD_ROLE": "reconciler",
    }


def reconcile(tmp_path: Path, env: dict[str, str], now: str = "2026-07-17T12:00:00Z") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(MANAGER), "reconcile-all", "--state-dir", str(tmp_path / "state"),
         "--audit-dir", str(tmp_path / "audit"), "--now", now],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )


def test_exact_version_set_extension_and_early_release_preserve_base_lock(tmp_path: Path) -> None:
    create_hold(tmp_path)
    env = fake_az(tmp_path)
    activated = reconcile(tmp_path, env)
    assert activated.returncode == 0, activated.stderr
    state_path = tmp_path / "state/incident-42.json"
    state = json.loads(state_path.read_text())
    immutable = [item["immutableUntil"] for item in state["versions"]]
    assert state["status"] == "active"
    assert all(item["appliedHold"] is True for item in state["versions"])
    assert (tmp_path / "az.log").read_text().count("x-ms-legal-hold=true") == 2

    extended = run_manager(
        tmp_path, "extend", "--hold-id", "incident-42",
        "--expires-at", "2026-12-15T12:00:00Z",
    )
    assert extended.returncode == 0, extended.stderr
    assert [item["immutableUntil"] for item in json.loads(state_path.read_text())["versions"]] == immutable

    released = run_manager(tmp_path, "release", "--hold-id", "incident-42")
    assert released.returncode == 0
    cleared = reconcile(tmp_path, env)
    assert cleared.returncode == 0
    state = json.loads(state_path.read_text())
    assert state["status"] == "released"
    assert all(item["deletionEligible"] is False for item in state["versions"])
    assert (tmp_path / "az.log").read_text().count("x-ms-legal-hold=false") == 2


def test_partial_operation_is_reconciling_and_expiry_clears_without_false_release(tmp_path: Path) -> None:
    create_hold(tmp_path)
    partial = reconcile(tmp_path, fake_az(tmp_path, "2026-07-17T00:01:00Z"))
    assert partial.returncode == 0
    state = json.loads((tmp_path / "state/incident-42.json").read_text())
    assert state["status"] == "reconciling"
    assert [item["appliedHold"] for item in state["versions"]] == [True, False]

    complete_env = fake_az(tmp_path)
    expired = reconcile(tmp_path, complete_env, "2026-12-02T12:00:00Z")
    assert expired.returncode == 0
    state = json.loads((tmp_path / "state/incident-42.json").read_text())
    assert state["status"] == "released"
    assert all(item["appliedHold"] is False for item in state["versions"])
    assert all(item["deletionEligible"] is True for item in state["versions"])


def test_reconciler_manifests_are_hourly_identity_bound_and_content_blind() -> None:
    kustomization = (RECONCILER / "kustomization.yaml").read_text()
    service_account = (RECONCILER / "service-account.yaml").read_text()
    cronjob = (RECONCILER / "cronjob.yaml").read_text()
    network = (RECONCILER / "network-policy.yaml").read_text()
    assert "0 * * * *" in cronjob
    assert "evidence-hold-reconciler" in service_account
    assert "${EVIDENCE_HOLD_RECONCILER_CLIENT_ID}" in service_account
    assert "EVIDENCE_HOLD_ROLE" in cronjob and "reconciler" in cronjob
    assert "manage-evidence-hold.sh" in cronjob and "reconcile-all" in cronjob
    for forbidden in ("download-batch", "blob list", "blob download", "blob delete", "immutability-policy"):
        assert forbidden not in cronjob
    assert "Ingress" in network and "Egress" in network
    assert set(re.findall(r"- ([a-z-]+\.yaml)", kustomization)) == {
        "namespace.yaml", "service-account.yaml", "cronjob.yaml", "network-policy.yaml",
    }


@pytest.mark.parametrize(
    "payload",
    [
        '{"client_secret":"not-allowed"}',
        '{"access_token":"not-allowed"}',
        '{"employeeId":"person-42"}',
        "kubeconfig: not-allowed",
        "-----BEGIN PRIVATE KEY-----",
    ],
)
def test_prohibited_evidence_content_is_rejected_before_retention(tmp_path: Path, payload: str) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text(payload)
    result = subprocess.run(
        [str(VALIDATE_EVIDENCE), "--file", str(evidence)],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "prohibited" in result.stderr
