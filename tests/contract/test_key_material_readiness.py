from pathlib import Path

from api.routes.health import MountedKeyMaterialProbe


def test_missing_key_material_fails_closed(tmp_path: Path) -> None:
    probe = MountedKeyMaterialProbe(
        certificate_path=tmp_path / "tls.crt", private_key_path=tmp_path / "tls.key",
        version_path=tmp_path / "version", expected_version="v1", expected_sans=frozenset({"core.test"}),
    )
    try:
        result = probe()
    except FileNotFoundError:
        result = False
    assert result is False
