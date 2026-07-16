from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
TERRAFORM = ROOT / "infra/azure/delivery-evidence-storage.tf"


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
    assert 'state                         = "Locked"' in evidence
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
