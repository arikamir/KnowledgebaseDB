from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PUBLISH = ROOT / "scripts/ci/publish-evidence.sh"
VALIDATE = ROOT / "scripts/ci/validate-evidence.sh"


def install_fakes(tmp_path: Path, upload_mode: str = "success") -> dict[str, str]:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "sleep").write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$1\" >> \"$SLEEP_LOG\"\n")
    (bindir / "az").write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "printf '%s\\n' \"$*\" >> \"$AZ_LOG\"\n"
        "if [[ \"$*\" == *'storage blob upload'* ]]; then\n"
        "  count=$(wc -l < \"$UPLOAD_COUNT\" 2>/dev/null || printf 0)\n"
        "  printf 'x\\n' >> \"$UPLOAD_COUNT\"\n"
        "  case \"$UPLOAD_MODE\" in\n"
        "    success) printf '%s\\n' '{\"versionId\":\"2026-07-17T12:00:00Z\",\"etag\":\"etag-1\"}'; exit 0 ;;\n"
        "    indeterminate-match) printf '%s\\n' 'connection reset' >&2; exit 1 ;;\n"
        "    exists) printf '%s\\n' 'HTTP 412 ConditionNotMet' >&2; exit 1 ;;\n"
        "    fail) printf '%s\\n' 'connection reset' >&2; exit 1 ;;\n"
        "  esac\n"
        "fi\n"
        "if [[ \"$*\" == *'storage blob show'* ]]; then\n"
        "  if [[ \"$UPLOAD_MODE\" == fail || \"$UPLOAD_MODE\" == exists ]]; then exit 1; fi\n"
        "  printf '%s\\n' \"{\\\"versionId\\\":\\\"2026-07-17T12:00:00Z\\\",\\\"etag\\\":\\\"etag-1\\\",\\\"metadata\\\":{\\\"evidence_sha256\\\":\\\"$EXPECTED_SHA\\\",\\\"evidence_length\\\":\\\"$EXPECTED_LENGTH\\\"}}\"\n"
        "fi\n"
    )
    for executable in bindir.iterdir():
        executable.chmod(0o755)
    return os.environ | {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "EVIDENCE_SLEEP_BIN": str(bindir / "sleep"),
        "SLEEP_LOG": str(tmp_path / "sleep.log"),
        "AZ_LOG": str(tmp_path / "az.log"),
        "UPLOAD_COUNT": str(tmp_path / "upload.count"),
        "UPLOAD_MODE": upload_mode,
    }


def evidence(tmp_path: Path) -> Path:
    path = tmp_path / "result.json"
    path.write_text('{"status":"passed","checks":3}\n')
    return path


def run_publish(tmp_path: Path, mode: str = "success") -> subprocess.CompletedProcess[str]:
    artifact = evidence(tmp_path)
    env = install_fakes(tmp_path, mode)
    import hashlib

    env["EXPECTED_SHA"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    env["EXPECTED_LENGTH"] = str(artifact.stat().st_size)
    return subprocess.run(
        [str(PUBLISH), "--file", str(artifact), "--environment", "nonprod",
         "--build-id", "build-42", "--stage", "pre-migration", "--artifact", "result.json",
         "--account", "stevidence0001", "--receipt", str(tmp_path / "receipt.json")],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )


def test_local_validation_rejects_secrets_personal_data_and_symlinks(tmp_path: Path) -> None:
    for payload in ('{"access_token":"secret"}', '{"email":"person@example.test"}', "kubeconfig: data"):
        candidate = tmp_path / f"bad-{len(list(tmp_path.iterdir()))}.json"
        candidate.write_text(payload)
        result = subprocess.run([str(VALIDATE), "--file", str(candidate)], text=True, capture_output=True)
        assert result.returncode != 0
    safe = evidence(tmp_path)
    link = tmp_path / "linked.json"
    link.symlink_to(safe)
    result = subprocess.run([str(VALIDATE), "--file", str(link)], text=True, capture_output=True)
    assert result.returncode != 0


def test_publish_uses_generated_immutable_path_and_exact_version_verification(tmp_path: Path) -> None:
    result = run_publish(tmp_path)
    assert result.returncode == 0, result.stderr
    calls = (tmp_path / "az.log").read_text()
    assert "--name deliveries/nonprod/build-42/pre-migration/result.json" in calls
    assert "--if-none-match * --overwrite false" in calls
    assert "storage blob show" in calls and "--version-id 2026-07-17T12:00:00Z" in calls
    assert "storage blob list" not in calls and "download" not in calls
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert receipt["authority"] == "azure-blob-version"
    assert receipt["controllerLocalAuthoritative"] is False


def test_indeterminate_upload_accepts_only_matching_exact_remote_version(tmp_path: Path) -> None:
    result = run_publish(tmp_path, "indeterminate-match")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "upload.count").read_text().count("x") == 1
    assert "--name deliveries/nonprod/build-42/pre-migration/result.json" in (tmp_path / "az.log").read_text()


def test_three_failed_attempts_use_one_four_sixteen_schedule(tmp_path: Path) -> None:
    result = run_publish(tmp_path, "fail")
    assert result.returncode != 0
    assert (tmp_path / "upload.count").read_text().count("x") == 3
    assert (tmp_path / "sleep.log").read_text().splitlines() == ["1", "4", "16"]
    assert not (tmp_path / "receipt.json").exists()


def test_precondition_collision_is_never_overwritten_or_retried(tmp_path: Path) -> None:
    result = run_publish(tmp_path, "exists")
    assert result.returncode != 0
    assert "overwrite denied" in result.stderr
    assert (tmp_path / "upload.count").read_text().count("x") == 1


def test_scripts_have_no_local_authoritative_archive_or_broad_storage_read() -> None:
    source = PUBLISH.read_text() + VALIDATE.read_text()
    assert "controllerLocalAuthoritative:false" in source
    assert "storage blob list" not in source
    assert "storage blob download" not in source
    assert "--overwrite false" in source
    assert "--if-none-match '*'" in source
