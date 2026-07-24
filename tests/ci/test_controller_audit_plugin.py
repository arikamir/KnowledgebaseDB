from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "jenkins-controller-audit-plugin"
JAVA = PLUGIN / "src/main/java/io/knowledgebasedb/jenkins/audit"
MANAGER = ROOT / "scripts/ci/manage-controller-audit.sh"
INSTALLER = ROOT / "scripts/jenkins/install-controller-audit-plugin.groovy"


def java(name: str) -> str:
    return (JAVA / name).read_text()


def test_listener_is_a_global_extension_and_creates_pending_action_without_scm_calls() -> None:
    listener = java("ControllerAuditRunListener.java")
    action = java("ControllerAuditAction.java")
    assert "@Extension" in listener and "extends RunListener<Run<?, ?>>" in listener
    assert "onStarted" in listener and "run.addAction(action)" in listener and "action.start()" in listener
    assert 'private String result = "pending"' in action
    assert "Jenkinsfile" not in listener and "shared" not in listener
    assert "SOURCE_REVISION" in listener


def test_every_transition_fsyncs_normal_run_and_append_only_replica() -> None:
    store = java("ControllerAuditStore.java")
    action = java("ControllerAuditAction.java")
    assert "run.save()" in store
    assert 'resolve("build.xml")' in store
    assert store.count("force(true)") >= 2
    assert "StandardOpenOption.APPEND" in store and "channel.lock()" in store
    assert "ControllerAuditStore.persistBoth(run, event)" in action
    assert 'controllerLocalAuthoritative", false' in action


def test_stage_updates_are_monotonic_and_terminal_finalization_is_exactly_once() -> None:
    action = java("ControllerAuditAction.java")
    assert "next < stageIndex" in action
    assert "if (terminalFinalized) return false" in action
    assert 'List.of("succeeded", "failed", "aborted", "aborted_recovered")' in action
    assert "terminalFinalized = true" in action
    assert "terminalFinalized = false" in action
    assert "onFinalized" in java("ControllerAuditRunListener.java")
    assert "doUpdate" in action and "doExport" in action
    assert 'STAGES.indexOf("evidence_active")' in action


def test_unhealthy_replica_or_unrecovered_mutation_blocks_protected_queue() -> None:
    store = java("ControllerAuditStore.java")
    dispatcher = java("ControllerAuditQueueDispatcher.java")
    assert 'resolve(".healthy")' in store and 'resolve(".recovery-block")' in store
    assert "static boolean writable()" in store and "static boolean healthy()" in store
    assert 'getParameter("PROTECTED_DELIVERY")' in dispatcher
    assert "protectedDelivery && !ControllerAuditStore.healthy()" in dispatcher
    assert "protected scheduling denied" in dispatcher


def test_restart_reconciliation_uses_all_sources_and_retains_ninety_days() -> None:
    maintenance = java("ControllerAuditMaintenance.java")
    store = java("ControllerAuditStore.java")
    for field in ("queueAccepted", "webhookAccepted", "azureEvidenceFound", "environmentMutated", "recoveryVerified"):
        assert field in maintenance
    assert 'finalizeOnce("aborted_recovered"' in maintenance
    assert "restoredFromReplica()" in maintenance
    assert "blockRecovery" in maintenance and "releaseRecovery" in maintenance
    assert "90L * 24 * 60 * 60 * 1000" in store
    assert "retentionCleanup()" in maintenance


def test_build_and_install_require_exact_protected_revision_and_hpi_digest() -> None:
    pom = (PLUGIN / "pom.xml").read_text()
    installer = INSTALLER.read_text()
    assert "env.GIT_COMMIT" in pom and "env.CONTROLLER_AUDIT_PROTECTED_REVISION" in pom
    assert "protected-revision-only" in pom and "Implementation-Build" in pom
    assert "CONTROLLER_AUDIT_SHA256" in installer and 'MessageDigest.getInstance("SHA-256")' in installer
    assert 'manifest.getValue("Implementation-Build") != protectedRevision' in installer
    assert 'manifest.getValue("Short-Name") != "controller-audit"' in installer
    assert "dynamicLoad(hpi)" in installer


def fake_http(tmp_path: Path) -> dict[str, str]:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    curl = bindir / "curl"
    curl.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$CURL_LOG\"\n"
        "if [[ \"$*\" == *'/export' ]]; then printf '%s\\n' '{\"schemaVersion\":1,\"result\":\"pending\",\"controllerLocalAuthoritative\":false}'; else printf '%s\\n' '{\"status\":\"updated\"}'; fi\n"
    )
    curl.chmod(0o755)
    netrc = tmp_path / "netrc"
    netrc.write_text("machine localhost login audit password redacted\n")
    crumb = tmp_path / "crumb"
    crumb.write_text("Jenkins-Crumb:value")
    return os.environ | {"PATH": f"{bindir}:{os.environ['PATH']}", "CURL_LOG": str(tmp_path / "curl.log")}, netrc, crumb


def test_repository_helper_can_only_request_allowed_updates_or_export(tmp_path: Path) -> None:
    env, netrc, crumb = fake_http(tmp_path)
    base = ["--run-url", "http://127.0.0.1:8080/job/release/42/", "--netrc-file", str(netrc), "--crumb-file", str(crumb)]
    updated = subprocess.run([str(MANAGER), "update", *base, "--stage", "agent_connected"], cwd=ROOT, env=env, text=True, capture_output=True)
    assert updated.returncode == 0
    denied = subprocess.run([str(MANAGER), "update", *base, "--stage", "succeeded"], cwd=ROOT, env=env, text=True, capture_output=True)
    assert denied.returncode != 0
    denied_create = subprocess.run([str(MANAGER), "create", *base], cwd=ROOT, env=env, text=True, capture_output=True)
    assert denied_create.returncode != 0
    output = tmp_path / "audit.json"
    exported = subprocess.run([str(MANAGER), "export", *base, "--output", str(output)], cwd=ROOT, env=env, text=True, capture_output=True)
    assert exported.returncode == 0 and json.loads(output.read_text())["controllerLocalAuthoritative"] is False
    source = MANAGER.read_text()
    assert '^(update|export)$' in source
    assert "/finalize" not in source and "/create" not in source and "/suppress" not in source
