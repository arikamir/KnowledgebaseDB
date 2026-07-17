from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/build-publish.sh"


def plan(path: Path, services: dict[str, bool]) -> Path:
    path.write_text(json.dumps({
        "sourceRevision": "a" * 40, "baselineRevision": "b" * 40,
        "services": services,
        "validationLanes": {"contractIntegrity": True, "readinessScenarios": False, "performanceProfile": False, "infrastructure": False},
        "reason": ["test"],
    }))
    return path


def toolchain(tmp_path: Path) -> dict[str, str]:
    binary = tmp_path / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text("""#!/usr/bin/env bash
printf 'docker %s\n' "$*" >> "$TOOL_LOG"
for ((i=1;i<=$#;i++)); do if [[ "${!i}" == "--metadata-file" ]]; then j=$((i+1)); printf '{"containerimage.digest":"sha256:%064d"}\n' 1 > "${!j}"; fi; done
""")
    trivy = binary / "trivy"
    trivy.write_text("""#!/usr/bin/env bash
printf 'trivy %s\n' "$*" >> "$TOOL_LOG"
for ((i=1;i<=$#;i++)); do if [[ "${!i}" == "--output" ]]; then j=$((i+1)); printf '{"Results":[],"SchemaVersion":2}\n' > "${!j}"; fi; done
""")
    syft = binary / "syft"
    syft.write_text("""#!/usr/bin/env bash
printf 'syft %s\n' "$*" >> "$TOOL_LOG"
for value in "$@"; do [[ "$value" == spdx-json=* ]] && printf '{"spdxVersion":"SPDX-2.3"}\n' > "${value#spdx-json=}"; done
""")
    az = binary / "az"
    az.write_text("#!/usr/bin/env bash\nprintf 'az %s\\n' \"$*\" >> \"$TOOL_LOG\"\n")
    for item in (docker, trivy, syft, az):
        item.chmod(0o755)
    return os.environ | {"PATH": f"{binary}:{os.environ['PATH']}", "TOOL_LOG": str(tmp_path / "tools.log")}


def run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(SCRIPT), *args], cwd=ROOT, env=toolchain(tmp_path), text=True, capture_output=True)


def test_publish_builds_selected_service_once_and_records_digest_provenance(tmp_path: Path) -> None:
    result = run(
        tmp_path, "publish", "--plan", str(plan(tmp_path / "plan.json", {"ui": True, "bff": False, "core": False})),
        "--build-id", "build-42", "--revision", "a" * 40, "--registry", "example.azurecr.io",
        "--output-dir", str(tmp_path / "out"), "--state-dir", str(tmp_path / "state"),
        "--now", "2026-07-17T12:00:00Z",
    )
    assert result.returncode == 0, result.stderr
    log = (tmp_path / "tools.log").read_text()
    assert log.count("docker buildx build") == 1
    assert "ui:quarantine-build-42" in log
    assert "bff:quarantine" not in log and "core:quarantine" not in log
    assert log.count("trivy image") == 1 and log.count("syft ") == 1
    manifest = json.loads((tmp_path / "out/release-manifest.json").read_text())
    assert list(manifest["services"]) == ["ui"]
    assert manifest["services"]["ui"]["image"].endswith("@sha256:" + "0" * 63 + "1")
    assert ":quarantine-" not in json.dumps(manifest)
    state = json.loads(next((tmp_path / "state").glob("*.json")).read_text())
    assert state["status"] == "published_unpromoted"
    for key in ("buildId", "sourceRevision", "scanEvidence", "sbomEvidence", "releaseManifestDigest"):
        assert state[key]


def test_docs_only_plan_emits_manifest_without_building(tmp_path: Path) -> None:
    result = run(
        tmp_path, "publish", "--plan", str(plan(tmp_path / "plan.json", {"ui": False, "bff": False, "core": False})),
        "--build-id", "docs-1", "--revision", "a" * 40, "--registry", "example.azurecr.io",
        "--output-dir", str(tmp_path / "out"), "--state-dir", str(tmp_path / "state"),
        "--now", "2026-07-17T12:00:00Z",
    )
    assert result.returncode == 0
    assert not (tmp_path / "tools.log").exists()
    assert json.loads((tmp_path / "out/release-manifest.json").read_text())["services"] == {}


def test_source_contains_fresh_gate_reuse_and_safe_gc_invariants() -> None:
    source = SCRIPT.read_text()
    for gate in ("validation", "scan", "identity", "evidence", "environment"):
        assert gate in source
    for required in ("published_unpromoted", "gc_eligible", "30 * 86400", "90 * 86400", "promoted", "held", "references", "releaseManifestDigest"):
        assert required in source
    assert "release alias" in source
    assert 'image="$repository@$digest"' in source


def test_gc_deletes_only_old_unreferenced_unheld_unpromoted_digest(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    evidence_dir = tmp_path / "evidence"
    state_dir.mkdir()
    old = datetime(2026, 5, 1, tzinfo=timezone.utc)
    base = {
        "schemaVersion": 1, "status": "published_unpromoted", "service": "ui",
        "digest": "sha256:" + "1" * 64, "publishedAt": old.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "promoted": False, "held": False, "references": 0,
    }
    (state_dir / "deletable.json").write_text(json.dumps(base))
    (state_dir / "held.json").write_text(json.dumps(base | {"digest": "sha256:" + "2" * 64, "held": True}))
    result = run(
        tmp_path, "gc", "--registry", "example.azurecr.io", "--state-dir", str(state_dir),
        "--evidence-dir", str(evidence_dir), "--now", "2026-07-17T12:00:00Z",
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "tools.log").read_text().count("az acr repository delete") == 1
    assert json.loads((state_dir / "deletable.json").read_text())["status"] == "gc_deleted"
    assert json.loads((state_dir / "held.json").read_text())["status"] == "published_unpromoted"
    assert list(evidence_dir.glob("*.json"))
