from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_contracts_declare_conditional_version_boundaries() -> None:
    bff = yaml.safe_load((ROOT / "specs/003-develop-ui/contracts/bff-api-v1.openapi.yaml").read_text())
    core = yaml.safe_load((ROOT / "specs/003-develop-ui/contracts/core-api-v1.openapi.yaml").read_text())
    assert "X-UI-Contract-Version" in str(bff)
    assert "X-BFF-Contract-Version" in str(core)


def test_runtime_sources_encode_all_stable_compatibility_failures() -> None:
    sources = "\n".join([
        (ROOT / "ui/src/app/compatibility.ts").read_text(),
        (ROOT / "bff/src/compatibility/core-version.ts").read_text(),
    ])
    for code in ("CONTRACT_VERSION_UNSUPPORTED", "CAPABILITY_METADATA_INVALID", "CAPABILITY_METADATA_UNAVAILABLE"):
        assert code in sources
