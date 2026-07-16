from scripts.ci.contract_gate import CORE_CONTRACT, validate_openapi


def test_core_contract_is_complete_and_has_unique_operations() -> None:
    summary = validate_openapi(CORE_CONTRACT)
    assert "getCoreCapabilities" in summary.operation_ids
    assert "createRoadmap" in summary.operation_ids
    assert summary.digest == "8364b04aa1be5a7a486e39d436eba7fbecdcc96ef86482d784436a3ea317946b"
