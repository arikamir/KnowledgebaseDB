from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts/ci/evidence-gate.sh"

REQUIRED = {
    "pre-promotion": ["artifact-provenance.json", "change-manifest.json", "release-manifest.json", "validation-summary.json"],
    "pre-migration": ["compatibility.json", "migration-plan.json", "schema-before.json"],
    "post-migration": ["migration-cleanup.json", "migration-result.json", "schema-after.json"],
    "pre-mutation": ["deployment-snapshot.json", "mutation-plan.json"],
    "post-mutation": ["mutation-journal.jsonl", "rollout.json"],
    "verification": ["deployment-snapshot.json", "smoke.json", "verification.json"],
    "rollback": ["rollback-journal.jsonl", "rollback-verification.json"],
}


def make_manifest(tmp_path: Path, stage: str, *, omit: str = "") -> Path:
    directory = tmp_path / stage
    directory.mkdir(exist_ok=True)
    artifacts = [name for name in REQUIRED[stage] if name != omit]
    for name in artifacts:
        (directory / name).write_text(json.dumps({"status": "passed", "artifact": name}) + "\n")
    manifest = directory / "evidence-manifest.json"
    manifest.write_text(json.dumps({
        "schemaVersion": 1, "environment": "nonprod", "buildId": "build-42",
        "stage": stage, "artifacts": artifacts,
    }))
    return manifest


def install_azure_fake(tmp_path: Path, fail_name: str = "") -> dict[str, str]:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    (bindir / "sleep").write_text("#!/usr/bin/env bash\n:\n")
    (bindir / "az").write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "printf '%s\\n' \"$*\" >> \"$AZ_LOG\"\n"
        "name=''; sha=''; length=''\n"
        "while (($#)); do\n"
        "  case \"$1\" in\n"
        "    --name) name=$2; shift 2 ;;\n"
        "    evidence_sha256=*) sha=${1#*=}; shift ;;\n"
        "    evidence_length=*) length=${1#*=}; shift ;;\n"
        "    *) shift ;;\n"
        "  esac\n"
        "done\n"
        "if [[ \"$AZ_LOG_LAST_CALL\" == upload ]]; then :; fi\n"
        "if [[ \"$(tail -n 1 \"$AZ_LOG\")\" == *'storage blob upload'* ]]; then\n"
        "  if [[ -n \"${FAIL_NAME:-}\" && \"$name\" == *\"$FAIL_NAME\" ]]; then printf 'connection reset\\n' >&2; exit 1; fi\n"
        "  jq --arg name \"$name\" --arg sha \"$sha\" --arg length \"$length\" '. + {($name):{sha:$sha,length:$length}}' \"$AZ_STATE\" > \"$AZ_STATE.tmp\"\n"
        "  mv \"$AZ_STATE.tmp\" \"$AZ_STATE\"\n"
        "  printf '{\"versionId\":\"version-%s\",\"etag\":\"etag\"}\\n' \"${sha:0:12}\"\n"
        "else\n"
        "  row=$(jq -c --arg name \"$name\" '.[$name] // empty' \"$AZ_STATE\")\n"
        "  [[ -n \"$row\" ]] || exit 1\n"
        "  sha=$(jq -r '.sha' <<<\"$row\"); length=$(jq -r '.length' <<<\"$row\")\n"
        "  printf '{\"versionId\":\"version-%s\",\"etag\":\"etag\",\"metadata\":{\"evidence_sha256\":\"%s\",\"evidence_length\":\"%s\"}}\\n' \"${sha:0:12}\" \"$sha\" \"$length\"\n"
        "fi\n"
    )
    for executable in bindir.iterdir():
        executable.chmod(0o755)
    state = tmp_path / "azure-state.json"
    state.write_text("{}")
    return os.environ | {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "EVIDENCE_SLEEP_BIN": str(bindir / "sleep"),
        "AZ_LOG": str(tmp_path / "az.log"),
        "AZ_STATE": str(state),
        "AZ_LOG_LAST_CALL": "unused",
        "FAIL_NAME": fail_name,
    }


def test_every_stage_requires_its_exact_complete_artifact_set(tmp_path: Path) -> None:
    for stage, artifacts in REQUIRED.items():
        valid = subprocess.run([str(GATE), "validate-manifest", "--manifest", str(make_manifest(tmp_path, stage))], cwd=ROOT, text=True, capture_output=True)
        assert valid.returncode == 0, f"{stage}: {valid.stderr}"
        missing_root = tmp_path / f"missing-{stage}"
        missing_root.mkdir()
        invalid = subprocess.run(
            [str(GATE), "validate-manifest", "--manifest", str(make_manifest(missing_root, stage, omit=artifacts[0]))],
            cwd=ROOT, text=True, capture_output=True,
        )
        assert invalid.returncode != 0


def test_gate_opens_only_after_artifacts_and_acceptance_are_authoritative(tmp_path: Path) -> None:
    env = install_azure_fake(tmp_path)
    gate_dir = tmp_path / "accepted-gate"
    published = subprocess.run(
        [str(GATE), "publish", "--manifest", str(make_manifest(tmp_path, "pre-mutation")),
         "--account", "stevidence0001", "--gate-dir", str(gate_dir)],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    assert published.returncode == 0, published.stderr
    acceptance = json.loads((gate_dir / "gate-acceptance.json").read_text())
    assert [item["artifact"] for item in acceptance["artifacts"]] == REQUIRED["pre-mutation"]
    assert all(item["authority"] == "azure-blob-version" for item in acceptance["artifacts"])
    checked = subprocess.run(
        [str(GATE), "check", "--gate-dir", str(gate_dir), "--stage", "pre-mutation"],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["gate"] == "open"
    calls = (tmp_path / "az.log").read_text()
    assert "gate-acceptance.json" in calls
    assert calls.count("storage blob upload") == 3


def test_partial_upload_never_materializes_an_open_gate(tmp_path: Path) -> None:
    env = install_azure_fake(tmp_path, fail_name="mutation-plan.json")
    gate_dir = tmp_path / "partial-gate"
    published = subprocess.run(
        [str(GATE), "publish", "--manifest", str(make_manifest(tmp_path, "pre-mutation")),
         "--account", "stevidence0001", "--gate-dir", str(gate_dir)],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    assert published.returncode != 0
    assert not gate_dir.exists()
    checked = subprocess.run(
        [str(GATE), "check", "--gate-dir", str(gate_dir), "--stage", "pre-mutation"],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    assert checked.returncode != 0


def test_gate_is_bound_to_the_requested_stage_and_immutable_acceptance(tmp_path: Path) -> None:
    env = install_azure_fake(tmp_path)
    gate_dir = tmp_path / "accepted-gate"
    assert subprocess.run(
        [str(GATE), "publish", "--manifest", str(make_manifest(tmp_path, "verification")),
         "--account", "stevidence0001", "--gate-dir", str(gate_dir)],
        cwd=ROOT, env=env,
    ).returncode == 0
    wrong_stage = subprocess.run(
        [str(GATE), "check", "--gate-dir", str(gate_dir), "--stage", "rollback"],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    assert wrong_stage.returncode != 0
    acceptance = gate_dir / "gate-acceptance.json"
    acceptance.chmod(0o600)
    changed = json.loads(acceptance.read_text())
    changed["status"] = "invented"
    acceptance.write_text(json.dumps(changed))
    tampered = subprocess.run(
        [str(GATE), "check", "--gate-dir", str(gate_dir), "--stage", "verification"],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    assert tampered.returncode != 0
