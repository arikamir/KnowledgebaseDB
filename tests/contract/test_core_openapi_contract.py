from scripts.ci.contract_gate import CORE_CONTRACT, validate_openapi


def test_core_contract_is_complete_and_has_unique_operations() -> None:
    summary = validate_openapi(CORE_CONTRACT)
    assert "getCoreCapabilities" in summary.operation_ids
    assert "createRoadmap" in summary.operation_ids
    assert summary.digest == "cae55080cb8e7bd974e5ab40416e6772604cb8bf11cf958269d11ac004fb590c"
