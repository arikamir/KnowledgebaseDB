from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from agent.lab_provider_policy import LabPolicyViolation, classify_applicability, destination_is_approved
from agent.lab_reference_validator import LabDestinationValidator, ValidationResponse
from tests.contract.test_lab_provider_approval import provider


NOW = datetime(2026, 7, 17, 10, tzinfo=timezone.utc)


@pytest.mark.parametrize("kind", ["command_execution", "configuration", "deployment", "troubleshooting", "observe_running_system", "borderline", "mixed", "unknown"])
def test_operational_borderline_mixed_and_unknown_objectives_require_labs(kind):
    decision = classify_applicability(kind, classifier_object_id="operator", classified_at=NOW, policy_version="v1")
    assert decision.lab_required and decision.omission_reason is None


@pytest.mark.parametrize("kind", ["orientation", "conceptual_comparison", "review_only"])
def test_only_three_omission_classes_are_allowed_with_complete_audit(kind):
    decision = classify_applicability(
        kind, classifier_object_id="operator", classified_at=NOW, policy_version="v1",
        omission_reason=kind, omission_explanation="This objective is intentionally non-operational.",
    )
    assert not decision.lab_required and decision.omission_reason == kind
    assert decision.classifier_object_id == "operator" and decision.classified_at == NOW


def test_missing_or_invalid_omission_evidence_and_security_override_fail_publication_policy():
    with pytest.raises(LabPolicyViolation, match="OMISSION_REASON_REQUIRED"):
        classify_applicability("orientation", classifier_object_id="operator", classified_at=NOW, policy_version="v1")
    with pytest.raises(LabPolicyViolation, match="OMISSION_EXPLANATION_INVALID"):
        classify_applicability("review_only", classifier_object_id="operator", classified_at=NOW, policy_version="v1", omission_reason="review_only", omission_explanation="too short")
    with pytest.raises(LabPolicyViolation, match="APPLICABILITY_OWNER_REQUIRED"):
        classify_applicability("orientation", classifier_object_id="security", classified_at=NOW, policy_version="v1", actor_role="security-reviewer", omission_reason="orientation", omission_explanation="This objective is intentionally non-operational.")


def test_only_https_destinations_on_the_approved_provider_domain_are_eligible():
    policy = provider(); policy["providers"] = [policy["providers"][0]]
    assert destination_is_approved(policy, "training-provider", "https://labs.example.com/session")
    assert destination_is_approved(policy, "training-provider", "https://child.labs.example.com/session")
    assert not destination_is_approved(policy, "training-provider", "http://labs.example.com/session")
    assert not destination_is_approved(policy, "training-provider", "https://example.net/session")
    assert not destination_is_approved(policy, "unknown", "https://labs.example.com/session")


@pytest.mark.parametrize("state,expected", [("active", "success"), ("reported", "success"), ("unavailable", "success"), ("retired", "final_failure")])
def test_persisted_policy_content_applicability_cost_and_state_are_validated_before_open(state, expected):
    calls = []
    validator = LabDestinationValidator(
        lambda url, timeout: calls.append((url, timeout)) or ValidationResponse(200, {}),
        resolve=lambda _host: ["8.8.8.8"],
    )
    reference = SimpleNamespace(
        content_version="content-v1", provider_policy_version="provider-v1",
        applicability_policy_version="applicability-v1", classifier_object_id="classifier",
        classified_at=NOW, cost_status="free", lab_required=True,
        omission_reason=None, omission_explanation=None, availability_state=state,
        destination_url="https://labs.example.com/start",
    )
    result = validator.validate_reference(reference, {"labs.example.com"})
    assert result.result == expected
    assert bool(calls) is (state != "retired")


def test_incomplete_pins_or_illegal_omission_fail_before_network_access():
    validator = LabDestinationValidator(lambda *_args: (_ for _ in ()).throw(AssertionError("network called")))
    reference = SimpleNamespace(
        content_version="", provider_policy_version="provider-v1",
        applicability_policy_version="applicability-v1", classifier_object_id="classifier",
        classified_at=NOW, cost_status="free", lab_required=False,
        omission_reason="orientation", omission_explanation="This objective is intentionally non-operational.",
        availability_state="active", destination_url="https://labs.example.com/start",
    )
    assert validator.validate_reference(reference, {"labs.example.com"}).error_code == "LAB_REFERENCE_PINS_INCOMPLETE"
    reference.content_version = "content-v1"; reference.omission_explanation = "short"
    assert validator.validate_reference(reference, {"labs.example.com"}).error_code == "LAB_APPLICABILITY_INVALID"
