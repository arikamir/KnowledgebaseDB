from scripts.ci.contract_gate import CORE_CONTRACT, validate_openapi


def test_core_contract_is_complete_and_has_unique_operations() -> None:
    summary = validate_openapi(CORE_CONTRACT)
    assert "getCoreCapabilities" in summary.operation_ids
    assert "createRoadmap" in summary.operation_ids
    assert summary.digest == "ecd043b615b2edbeb2b9e206d5989c1495b8981ed47a578bd36edcac917bdb1b"
