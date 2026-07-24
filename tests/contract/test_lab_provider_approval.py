from copy import deepcopy
from pathlib import Path

import json
import pytest
import yaml

from agent.lab_provider_policy import LabPolicyViolation, validate_provider_change


ROOT = Path(__file__).resolve().parents[2]
POLICY = yaml.safe_load((ROOT / "config/approved-lab-providers.yaml").read_text())


def provider():
    owner_group = "11111111-1111-4111-8111-111111111111"
    security_group = "22222222-2222-4222-8222-222222222222"
    return {
        "policyVersion": "lab-provider-policy-v1",
        "groups": {
            "learningContentOwnersObjectId": owner_group,
            "applicationSecurityReviewersObjectId": security_group,
        },
        "providers": [{
            "providerId": "training-provider", "displayName": "Training Provider",
            "domains": ["labs.example.com"],
            "reason": "Approved hands-on training destination for the pilot.",
            "effectiveAt": "2026-07-17T10:00:00Z", "policyVersion": "lab-provider-policy-v1",
            "auditReference": "AUDIT-LABS-001",
            "approvals": {
                "learningContentOwner": {
                    "approverObjectId": "33333333-3333-4333-8333-333333333333",
                    "memberOfGroupObjectId": owner_group,
                    "membershipEvidence": {"source": "microsoft-entra-group-membership", "verifiedAt": "2026-07-17T09:00:00Z", "auditReference": "ENTRA-OWNER-001"},
                },
                "applicationSecurityReviewer": {
                    "approverObjectId": "44444444-4444-4444-8444-444444444444",
                    "memberOfGroupObjectId": security_group,
                    "membershipEvidence": {"source": "microsoft-entra-group-membership", "verifiedAt": "2026-07-17T09:01:00Z", "auditReference": "ENTRA-SECURITY-001"},
                },
            },
        }],
    }


def test_initial_allowlist_is_schema_valid_and_empty():
    schema = json.loads((ROOT / "config/lab-provider-policy.schema.json").read_text())
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(schema["required"]) == {"schemaVersion", "policyVersion", "groups", "providers"}
    assert schema["properties"]["providers"]["items"] == {"$ref": "#/$defs/provider"}
    assert POLICY["schemaVersion"] == schema["properties"]["schemaVersion"]["const"]
    assert POLICY["providers"] == []
    assert POLICY["groups"] == {
        "learningContentOwnersObjectId": "${LEARNING_CONTENT_OWNERS_GROUP_OBJECT_ID}",
        "applicationSecurityReviewersObjectId": "${APPLICATION_SECURITY_REVIEWERS_GROUP_OBJECT_ID}",
    }


def test_distinct_group_members_with_evidence_can_approve_provider_and_domain_expansion():
    policy = provider()
    validate_provider_change(policy, policy["providers"][0])
    expanded = deepcopy(policy["providers"][0])
    expanded["domains"].append("advanced-labs.example.com")
    expanded["auditReference"] = "AUDIT-LABS-EXPANSION-002"
    validate_provider_change(policy, expanded)


@pytest.mark.parametrize("missing", ["learningContentOwner", "applicationSecurityReviewer"])
def test_both_approvals_are_required(missing):
    policy = provider(); item = policy["providers"][0]
    del item["approvals"][missing]
    with pytest.raises(LabPolicyViolation, match="DUAL_APPROVAL_REQUIRED"):
        validate_provider_change(policy, item)


def test_one_human_cannot_self_approve_even_when_in_both_groups():
    policy = provider(); item = policy["providers"][0]
    item["approvals"]["applicationSecurityReviewer"]["approverObjectId"] = item["approvals"]["learningContentOwner"]["approverObjectId"]
    with pytest.raises(LabPolicyViolation, match="DISTINCT_HUMAN"):
        validate_provider_change(policy, item)


def test_wrong_group_missing_membership_evidence_and_policy_drift_fail_closed():
    policy = provider(); item = policy["providers"][0]
    item["approvals"]["learningContentOwner"]["memberOfGroupObjectId"] = policy["groups"]["applicationSecurityReviewersObjectId"]
    with pytest.raises(LabPolicyViolation, match="GROUP_MEMBERSHIP"):
        validate_provider_change(policy, item)
    policy = provider(); item = policy["providers"][0]
    del item["approvals"]["applicationSecurityReviewer"]["membershipEvidence"]["auditReference"]
    with pytest.raises(LabPolicyViolation, match="MEMBERSHIP_EVIDENCE"):
        validate_provider_change(policy, item)
    policy = provider(); item = policy["providers"][0]; item["policyVersion"] = "stale-policy"
    with pytest.raises(LabPolicyViolation, match="POLICY_VERSION_MISMATCH"):
        validate_provider_change(policy, item)
