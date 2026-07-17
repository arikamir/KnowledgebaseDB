from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PROMOTE = ROOT / "scripts/ci/promote.sh"
ROLLBACK = ROOT / "scripts/ci/rollback.sh"
JOURNAL = ROOT / "scripts/ci/mutation-journal.sh"
REGISTRY = "career.azurecr.io"


def image(service: str, digit: str) -> str:
    return f"{REGISTRY}/devops-career-agent-{service}@sha256:{digit * 64}"


def install_fakes(tmp_path: Path) -> dict[str, str]:
    state = tmp_path / "cluster.json"
    state.write_text(json.dumps({service: image(service, "1") for service in ("ui", "bff", "core")}))
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "kubectl").write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "printf '%s\\n' \"$*\" >> \"$KUBE_LOG\"\n"
        "if [[ \"$*\" == *' get deployment '* ]]; then\n"
        "  service=${5}\n"
        "  value=$(jq -r --arg service \"$service\" '.[$service]' \"$CLUSTER_STATE\")\n"
        "  jq -cn --arg service \"$service\" --arg image \"$value\" '{spec:{template:{spec:{containers:[{name:$service,image:$image}]}}}}'\n"
        "elif [[ \"$*\" == *' set image '* ]]; then\n"
        "  assignment=${6}; service=${assignment%%=*}; value=${assignment#*=}\n"
        "  if [[ \"${FAIL_RESTORE_SERVICE:-}\" == \"$service\" && \"$value\" == *\"sha256:${ORIGINAL_DIGIT:-1}\"* ]]; then exit 1; fi\n"
        "  jq --arg service \"$service\" --arg value \"$value\" '.[$service]=$value' \"$CLUSTER_STATE\" > \"$CLUSTER_STATE.tmp\"\n"
        "  mv \"$CLUSTER_STATE.tmp\" \"$CLUSTER_STATE\"\n"
        "  if [[ \"${LOSE_FORWARD_RESPONSE:-}\" == \"$service\" && \"$value\" != *\"sha256:${ORIGINAL_DIGIT:-1}\"* ]]; then exit 1; fi\n"
        "elif [[ \"$*\" == *' rollout status '* ]]; then exit 0\n"
        "else exit 2\n"
        "fi\n"
    )
    (bindir / "curl").write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "printf '%s\\n' \"$*\" >> \"$CURL_LOG\"\n"
        "url=${!#}\n"
        "if [[ -n \"${FAIL_SMOKE_ONCE:-}\" && \"$url\" == *\"$FAIL_SMOKE_ONCE\"* && ! -e \"$SMOKE_FAILED\" ]]; then : > \"$SMOKE_FAILED\"; exit 1; fi\n"
    )
    (bindir / "sleep").write_text("#!/usr/bin/env bash\nprintf '%s\\n' \"$1\" >> \"$SLEEP_LOG\"\n")
    (bindir / "now").write_text("#!/usr/bin/env bash\nprintf '1000\\n'\n")
    for executable in bindir.iterdir():
        executable.chmod(0o755)
    return os.environ | {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "CLUSTER_STATE": str(state),
        "KUBE_LOG": str(tmp_path / "kubectl.log"),
        "CURL_LOG": str(tmp_path / "curl.log"),
        "SLEEP_LOG": str(tmp_path / "sleep.log"),
        "SMOKE_FAILED": str(tmp_path / "smoke.failed"),
        "DELIVERY_SLEEP_BIN": str(bindir / "sleep"),
        "DELIVERY_NOW_BIN": str(bindir / "now"),
        "CORE_SMOKE_URL": "https://core.test/health/ready",
        "BFF_SMOKE_URL": "https://bff.test/health/ready",
        "UI_SMOKE_URL": "https://ui.test/health/ready",
    }


def manifest(tmp_path: Path, tag: bool = False) -> Path:
    path = tmp_path / "release-manifest.json"
    services = {
        service: {"image": f"{REGISTRY}/devops-career-agent-{service}:latest" if tag else image(service, digit)}
        for service, digit in (("ui", "7"), ("bff", "8"), ("core", "9"))
    }
    path.write_text(json.dumps({"schemaVersion": 1, "selectorPolicy": "digest-only", "services": services}))
    return path


def promote(tmp_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PROMOTE), "--manifest", str(manifest(tmp_path)), "--journal-dir", str(tmp_path / "journal"),
         "--attempt", "build-42", "--environment", "nonprod", "--snapshot-out", str(tmp_path / "snapshot.json")],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )


def events(tmp_path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (tmp_path / "journal/build-42.jsonl").read_text().splitlines()]


def test_digest_only_promotion_snapshots_all_services_and_runs_core_bff_ui(tmp_path: Path) -> None:
    env = install_fakes(tmp_path)
    result = promote(tmp_path, env)
    assert result.returncode == 0, result.stderr
    snapshot = json.loads((tmp_path / "journal/build-42.snapshot.json").read_text())
    assert list(snapshot["services"]) == ["bff", "core", "ui"]
    calls = [line for line in (tmp_path / "kubectl.log").read_text().splitlines() if " set image " in line]
    assert ["deployment/core", "deployment/bff", "deployment/ui"] == [next(part for part in call.split() if part.startswith("deployment/")) for call in calls]
    assert events(tmp_path)[-1]["result"] == "promoted"
    assert subprocess.run([str(JOURNAL), "verify", "--journal-dir", str(tmp_path / "journal"), "--attempt", "build-42"], cwd=ROOT).returncode == 0


def test_tag_selector_is_rejected_before_snapshot_or_mutation(tmp_path: Path) -> None:
    env = install_fakes(tmp_path)
    result = subprocess.run(
        [str(PROMOTE), "--manifest", str(manifest(tmp_path, tag=True)), "--journal-dir", str(tmp_path / "journal"),
         "--attempt", "build-42", "--environment", "nonprod", "--snapshot-out", str(tmp_path / "snapshot.json")],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert not (tmp_path / "snapshot.json").exists()


def test_failure_restores_every_changed_service_in_reverse_order(tmp_path: Path) -> None:
    env = install_fakes(tmp_path) | {"FAIL_SMOKE_ONCE": "ui.test"}
    result = promote(tmp_path, env)
    assert result.returncode != 0
    assert json.loads((tmp_path / "cluster.json").read_text()) == {service: image(service, "1") for service in ("ui", "bff", "core")}
    calls = [line for line in (tmp_path / "kubectl.log").read_text().splitlines() if " set image " in line]
    reversed_services = [next(part for part in call.split() if part.startswith("deployment/")) for call in calls[-3:]]
    assert reversed_services == ["deployment/ui", "deployment/bff", "deployment/core"]
    assert events(tmp_path)[-1]["result"] == "rolled_back"


def test_lost_mutation_response_is_observed_and_compensated(tmp_path: Path) -> None:
    env = install_fakes(tmp_path) | {"LOSE_FORWARD_RESPONSE": "bff"}
    result = promote(tmp_path, env)
    assert result.returncode != 0
    state = json.loads((tmp_path / "cluster.json").read_text())
    assert state == {service: image(service, "1") for service in ("ui", "bff", "core")}
    bff_events = [item for item in events(tmp_path) if item["service"] == "bff"]
    assert any(item["result"] == "mutation-applied-response-lost" for item in bff_events)
    assert any(item["event"] == "reverse_verified" for item in bff_events)


def test_rollback_failure_stops_in_order_quarantines_and_requires_distinct_recovery(tmp_path: Path) -> None:
    env = install_fakes(tmp_path) | {"FAIL_SMOKE_ONCE": "ui.test", "FAIL_RESTORE_SERVICE": "bff"}
    result = promote(tmp_path, env)
    assert result.returncode != 0
    journal_events = events(tmp_path)
    failures = [item for item in journal_events if item["event"] == "reverse_failed" and item["service"] == "bff"]
    assert [item["compensationAttempt"] for item in failures] == [1, 2, 3]
    assert (tmp_path / "sleep.log").read_text().splitlines()[-4:] == ["0", "0", "15", "45"]
    assert journal_events[-1]["result"] == "rollback_failed"
    assert (tmp_path / "journal/build-42.quarantine.json").exists()
    assert json.loads((tmp_path / "cluster.json").read_text())["core"] == image("core", "9")

    denied = subprocess.run(
        [str(ROLLBACK), "recover", "--journal-dir", str(tmp_path / "journal"), "--attempt", "build-42",
         "--namespace", "nonprod", "--operator", "person-1", "--approver", "person-1",
         "--operator-role", "delivery-recovery-operator", "--approver-role", "platform-operations"],
        cwd=ROOT, env=env, text=True, capture_output=True,
    )
    assert denied.returncode != 0

    recovered_env = env.copy()
    recovered_env.pop("FAIL_RESTORE_SERVICE")
    recovered = subprocess.run(
        [str(ROLLBACK), "recover", "--journal-dir", str(tmp_path / "journal"), "--attempt", "build-42",
         "--namespace", "nonprod", "--operator", "recovery-operator", "--approver", "platform-approver",
         "--operator-role", "delivery-recovery-operator", "--approver-role", "platform-operations"],
        cwd=ROOT, env=recovered_env, text=True, capture_output=True,
    )
    assert recovered.returncode == 0, recovered.stderr
    assert json.loads((tmp_path / "cluster.json").read_text()) == {service: image(service, "1") for service in ("ui", "bff", "core")}
    assert (tmp_path / "journal/build-42.quarantine.json.released").exists()
    assert events(tmp_path)[-1]["result"] == "recovered"


def test_hash_chain_detects_rewritten_history(tmp_path: Path) -> None:
    env = install_fakes(tmp_path)
    assert promote(tmp_path, env).returncode == 0
    path = tmp_path / "journal/build-42.jsonl"
    path.chmod(0o600)
    path.write_text(path.read_text().replace("rollout-and-smoke-passed", "invented-result", 1))
    checked = subprocess.run(
        [str(JOURNAL), "verify", "--journal-dir", str(tmp_path / "journal"), "--attempt", "build-42"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert checked.returncode != 0


def test_snapshot_digest_detects_rewritten_pre_attempt_state(tmp_path: Path) -> None:
    env = install_fakes(tmp_path)
    assert promote(tmp_path, env).returncode == 0
    snapshot = tmp_path / "journal/build-42.snapshot.json"
    snapshot.chmod(0o600)
    snapshot.write_text(snapshot.read_text().replace("sha256:111", "sha256:211", 1))
    checked = subprocess.run(
        [str(JOURNAL), "verify", "--journal-dir", str(tmp_path / "journal"), "--attempt", "build-42"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert checked.returncode != 0


def test_total_twenty_minute_deadline_stops_before_out_of_order_compensation(tmp_path: Path) -> None:
    env = install_fakes(tmp_path) | {"FAIL_SMOKE_ONCE": "ui.test"}
    deadline_now = tmp_path / "bin/deadline-now"
    deadline_now.write_text(
        "#!/usr/bin/env bash\n"
        "value=1000\n"
        "if [[ -e \"$NOW_STATE\" ]]; then value=2200; else : > \"$NOW_STATE\"; fi\n"
        "printf '%s\\n' \"$value\"\n"
    )
    deadline_now.chmod(0o755)
    env |= {"DELIVERY_NOW_BIN": str(deadline_now), "NOW_STATE": str(tmp_path / "now.state")}
    result = promote(tmp_path, env)
    assert result.returncode != 0
    journal_events = events(tmp_path)
    assert not [item for item in journal_events if item["event"] == "reverse_attempt"]
    assert journal_events[-1]["result"] == "rollback_failed"
