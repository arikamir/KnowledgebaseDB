from pathlib import Path

from scripts.ci.contract_gate import BFF_CONTRACT, validate_openapi


def test_bff_contract_is_complete_and_has_unique_operations() -> None:
    summary = validate_openapi(BFF_CONTRACT)
    assert "getBffCapabilities" in summary.operation_ids
    assert "createBrowserRoadmap" in summary.operation_ids
    assert summary.digest == "68d4c6d0d344bc46a1bef5e1cd397cd04f9bde436cf50b3cb144bddf4891ee1a"
    assert Path(BFF_CONTRACT).is_file()
