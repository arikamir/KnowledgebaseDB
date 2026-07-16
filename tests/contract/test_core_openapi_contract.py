from scripts.ci.contract_gate import CORE_CONTRACT, validate_openapi


def test_core_contract_is_complete_and_has_unique_operations() -> None:
    summary = validate_openapi(CORE_CONTRACT)
    assert "getCoreCapabilities" in summary.operation_ids
    assert "createRoadmap" in summary.operation_ids
    assert summary.digest == "7f606039a81813ad3d35cf1047d2e29bd84bde044aef476084f37f93455a3ca3"
