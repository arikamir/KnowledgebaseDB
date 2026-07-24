"""Lab applicability and dual-human provider approval policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse


REQUIRED_OBJECTIVES = frozenset({
    "command_execution", "configuration", "deployment", "troubleshooting",
    "observe_running_system", "borderline", "mixed",
})
ALLOWED_OMISSIONS = frozenset({"orientation", "conceptual_comparison", "review_only"})


class LabPolicyViolation(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ApplicabilityDecision:
    lab_required: bool
    omission_reason: str | None
    omission_explanation: str | None
    classifier_object_id: str
    classified_at: datetime
    policy_version: str


def classify_applicability(
    objective_kind: str,
    *,
    classifier_object_id: str,
    classified_at: datetime,
    policy_version: str,
    actor_role: str = "learning-content-operations",
    omission_reason: str | None = None,
    omission_explanation: str | None = None,
) -> ApplicabilityDecision:
    if actor_role != "learning-content-operations":
        raise LabPolicyViolation("APPLICABILITY_OWNER_REQUIRED")
    if not classifier_object_id or not policy_version or classified_at.tzinfo is None:
        raise LabPolicyViolation("APPLICABILITY_AUDIT_INCOMPLETE")
    required = objective_kind not in ALLOWED_OMISSIONS or objective_kind in REQUIRED_OBJECTIVES
    if required:
        if omission_reason is not None or omission_explanation is not None:
            raise LabPolicyViolation("LAB_REQUIRED")
        return ApplicabilityDecision(True, None, None, classifier_object_id, classified_at, policy_version)
    if omission_reason != objective_kind:
        raise LabPolicyViolation("OMISSION_REASON_REQUIRED")
    if omission_explanation is None or not 20 <= len(omission_explanation.strip()) <= 500:
        raise LabPolicyViolation("OMISSION_EXPLANATION_INVALID")
    return ApplicabilityDecision(False, omission_reason, omission_explanation.strip(), classifier_object_id, classified_at, policy_version)


def validate_provider_change(policy: dict, provider: dict) -> None:
    groups = policy["groups"]
    approvals = provider.get("approvals", {})
    owner = approvals.get("learningContentOwner")
    security = approvals.get("applicationSecurityReviewer")
    if owner is None or security is None:
        raise LabPolicyViolation("DUAL_APPROVAL_REQUIRED")
    if owner["approverObjectId"] == security["approverObjectId"]:
        raise LabPolicyViolation("DISTINCT_HUMAN_APPROVERS_REQUIRED")
    expected = (
        (owner, groups["learningContentOwnersObjectId"]),
        (security, groups["applicationSecurityReviewersObjectId"]),
    )
    for approval, group_id in expected:
        if approval.get("memberOfGroupObjectId") != group_id:
            raise LabPolicyViolation("APPROVER_GROUP_MEMBERSHIP_REQUIRED")
        evidence = approval.get("membershipEvidence", {})
        if evidence.get("source") != "microsoft-entra-group-membership" or not evidence.get("verifiedAt") or not evidence.get("auditReference"):
            raise LabPolicyViolation("MEMBERSHIP_EVIDENCE_REQUIRED")
    if provider.get("policyVersion") != policy.get("policyVersion"):
        raise LabPolicyViolation("POLICY_VERSION_MISMATCH")
    if not provider.get("auditReference") or not provider.get("reason"):
        raise LabPolicyViolation("PROVIDER_AUDIT_INCOMPLETE")
    domains = provider.get("domains", [])
    if not domains or len(domains) != len(set(domains)):
        raise LabPolicyViolation("PROVIDER_DOMAINS_INVALID")


def destination_is_approved(policy: dict, provider_id: str, destination: str) -> bool:
    parsed = urlparse(destination)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    provider = next((item for item in policy.get("providers", []) if item.get("providerId") == provider_id), None)
    if provider is None:
        return False
    validate_provider_change(policy, provider)
    hostname = parsed.hostname.casefold()
    return any(hostname == domain.casefold() or hostname.endswith(f".{domain.casefold()}") for domain in provider["domains"])
