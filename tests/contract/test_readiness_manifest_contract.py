from scripts.ci.contract_gate import validate_readiness_manifest


def test_readiness_manifest_digest_and_denominators() -> None:
    validate_readiness_manifest()
