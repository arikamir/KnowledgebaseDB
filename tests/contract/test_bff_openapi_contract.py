from pathlib import Path

from scripts.ci.contract_gate import BFF_CONTRACT, validate_openapi


def test_bff_contract_is_complete_and_has_unique_operations() -> None:
    summary = validate_openapi(BFF_CONTRACT)
    assert "getBffCapabilities" in summary.operation_ids
    assert "createBrowserRoadmap" in summary.operation_ids
    assert summary.digest == "9a19d1205ac94d0197efa9db716ba2e11b36422a40ad59fab220d00fc6815bb9"
    assert Path(BFF_CONTRACT).is_file()
