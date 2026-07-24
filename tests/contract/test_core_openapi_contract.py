from scripts.ci.contract_gate import CORE_CONTRACT, validate_openapi


def test_core_contract_is_complete_and_has_unique_operations() -> None:
    summary = validate_openapi(CORE_CONTRACT)
    assert "getCoreCapabilities" in summary.operation_ids
    assert "createRoadmap" in summary.operation_ids
    assert summary.digest == "74eb81eed70e24183862bd187ab9f9bfa778d2992efeae54b397e2d36df19497"
