from scripts.ci.contract_gate import (
    BFF_CONTRACT,
    CORE_CONTRACT,
    validate_interaction_profile,
    validate_openapi,
    validate_performance_profile,
)


def test_both_approved_performance_profiles_are_digest_bound() -> None:
    summaries = (validate_openapi(BFF_CONTRACT), validate_openapi(CORE_CONTRACT))
    validate_performance_profile(summaries)
    validate_interaction_profile(summaries)
