from pathlib import Path

from scripts.ci.contract_gate import BFF_CONTRACT, validate_openapi


def test_bff_contract_is_complete_and_has_unique_operations() -> None:
    summary = validate_openapi(BFF_CONTRACT)
    assert "getBffCapabilities" in summary.operation_ids
    assert "createBrowserRoadmap" in summary.operation_ids
    assert summary.digest == "faa3e1303bc6b4e0b3e84ecbe9ef5e08bf9608121dbdcc9c9a0e2a081a20ff02"
    assert Path(BFF_CONTRACT).is_file()
