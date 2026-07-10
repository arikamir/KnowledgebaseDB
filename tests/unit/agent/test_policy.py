from __future__ import annotations

from agent.policy import classify_request, is_boundary_violation


def test_classify_request_blocks_hr_and_compensation_language():
    decision = classify_request("I need help preparing for my performance review and salary discussion.")

    assert not decision.allowed
    assert decision.category == "hr"
    assert "performance review" in decision.matched_terms or "salary" in decision.matched_terms
    assert decision.suggested_action is not None


def test_classify_request_blocks_performance_management_language():
    decision = classify_request("Can you help me with employee evaluation and calibration?")

    assert not decision.allowed
    assert decision.category == "performance"
    assert decision.matched_terms
    assert is_boundary_violation("Can you help me with employee evaluation and calibration?")


def test_classify_request_allows_career_growth_guidance():
    decision = classify_request("I want to move from Windows admin into DevOps with Kubernetes.")

    assert decision.allowed
    assert decision.category is None

