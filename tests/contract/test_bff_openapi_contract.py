from pathlib import Path

from scripts.ci.contract_gate import BFF_CONTRACT, validate_openapi


def test_bff_contract_is_complete_and_has_unique_operations() -> None:
    summary = validate_openapi(BFF_CONTRACT)
    assert "getBffCapabilities" in summary.operation_ids
    assert "createBrowserRoadmap" in summary.operation_ids
    assert summary.digest == "2b10d27294ebaa5fb915006e1f08b6922cd7cc5d138d857b88ddfa9b11063577"
    assert Path(BFF_CONTRACT).is_file()
