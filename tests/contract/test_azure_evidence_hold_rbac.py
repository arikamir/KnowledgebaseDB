from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RBAC = ROOT / "infra/azure/delivery-evidence-hold-managers.tf"


def block(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_hold_managers_are_group_scoped_to_control_and_audit_only() -> None:
    text = RBAC.read_text()
    manager = block(
        text,
        'resource "azurerm_role_definition" "evidence_hold_manager_control"',
        'resource "azurerm_role_assignment" "evidence_hold_manager_inventory"',
    )
    assignments = block(
        text,
        'resource "azurerm_role_assignment" "evidence_hold_manager_inventory"',
        'resource "azurerm_role_definition" "evidence_hold_inventory_reader"',
    )
    assert "blobs/add/action" in manager and "blobs/write" in manager and "blobs/read" in manager
    for denied in ("listKeys/action", "containers/write", "containers/delete", "immutabilityPolicies/*", "setLegalHold/action", "clearLegalHold/action", "blobs/delete", "tags/write"):
        assert denied in manager
    assert assignments.count("local.effective_evidence_hold_managers_group_object_id") == 2
    assert assignments.count('principal_type     = "Group"') == 2
    assert "evidence_hold_inventory.id" in assignments
    assert "evidence_hold_audit.id" in assignments
    assert "delivery_evidence.id" not in assignments


def test_reconciler_inventory_role_is_read_only_and_separately_scoped() -> None:
    text = RBAC.read_text()
    reader = block(
        text,
        'resource "azurerm_role_definition" "evidence_hold_inventory_reader"',
        'resource "azurerm_role_assignment" "evidence_hold_reconciler_inventory"',
    )
    assignment = block(
        text,
        'resource "azurerm_role_assignment" "evidence_hold_reconciler_inventory"',
        'resource "azurerm_role_definition" "evidence_version_hold_reconciler"',
    )
    assert 'data_actions     = ["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"]' in reader
    assert "blobs/write" in reader and "blobs/delete" in reader
    assert "evidence_hold_inventory.id" in assignment
    assert 'workload["evidence-hold-reconciler"].principal_id' in assignment
    assert "evidence_hold_audit" not in assignment and "delivery_evidence" not in assignment


def test_version_hold_role_has_one_authorizing_action_and_no_content_action() -> None:
    text = RBAC.read_text()
    role = block(
        text,
        'resource "azurerm_role_definition" "evidence_version_hold_reconciler"',
        'resource "azurerm_role_assignment" "evidence_hold_reconciler_versions"',
    )
    assignment = block(
        text,
        'resource "azurerm_role_assignment" "evidence_hold_reconciler_versions"',
        "locals {",
    )
    assert 'actions = ["Microsoft.Storage/storageAccounts/blobServices/containers/write"]' in role
    assert "data_actions = []" in role
    for denied in ("containers/read", "containers/delete", "immutabilityPolicies/*", "setLegalHold/action", "clearLegalHold/action", "blobs/read", "blobs/write", "blobs/delete", "permanentDelete/action"):
        assert denied in role
    assert "azurerm_storage_container.delivery_evidence.id" in assignment
    assert 'workload["evidence-hold-reconciler"].principal_id' in assignment


def test_runtime_enforces_complete_exact_version_inventory() -> None:
    script = (ROOT / "scripts/ci/manage-evidence-hold.sh").read_text()
    assert ".inventoryComplete == true" in script
    assert ".expectedVersionCount == (.versions | length)" in script
    assert "?comp=legalhold&versionid=${version}" in script
    assert '"x-ms-legal-hold=${desired}"' in script
    for forbidden in ("az storage blob list", "az storage blob download", "immutability-policy"):
        assert forbidden not in script
