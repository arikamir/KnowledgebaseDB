from scripts.ci.contract_gate import validate_all


def test_authoritative_contract_gate_passes_without_mutation() -> None:
    assert set(validate_all()) == {"bff-api-v1", "core-api-v1"}
