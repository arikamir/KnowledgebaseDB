from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timedelta, timezone


ROOT = Path(__file__).resolve().parents[2]
DIGEST = ROOT / "scripts/azure/compute-platform-configuration-digest.sh"
PREFLIGHT = ROOT / "scripts/azure/preflight-ui-platform.sh"
BOOTSTRAP = ROOT / "scripts/azure/bootstrap-ui-platform.sh"
FINALIZE = ROOT / "scripts/azure/finalize-ui-platform.sh"


def test_digest_policy_is_non_self_referential_and_explicitly_excludes_local_state() -> None:
    policy = json.loads((ROOT / "config/platform-configuration-digest-v1.yaml").read_text())
    assert "config/platform-configuration-digest-v1.yaml" in policy["includes"]
    assert "config/platform-bootstrap-nonprod.json" in policy["excludes"]
    for pattern in ("**/*.tfstate", "**/*.tfplan", "**/terraform.tfvars", "**/.git/**", "**/*.log", "**/.env*"):
        assert pattern in policy["excludes"]
    assert not any("platform-bootstrap-nonprod" in item for item in policy["includes"])


def test_digest_changes_for_content_mode_add_remove_and_rename(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    (repo / "infra/azure").mkdir(parents=True)
    policy = {"schemaVersion": 1, "algorithm": "sha256-canonical-path-mode-length-content-v1", "includes": ["config/platform-configuration-digest-v1.yaml", "infra/azure/*.tf"], "excludes": []}
    policy_path = repo / "config/platform-configuration-digest-v1.yaml"
    policy_path.write_text(json.dumps(policy))
    item = repo / "infra/azure/main.tf"
    item.write_text("resource {}\n")

    def calculate() -> dict:
        result = subprocess.run([str(DIGEST), str(repo)], cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    initial = calculate()
    item.write_text("resource { changed = true }\n")
    content = calculate(); assert content["digest"] != initial["digest"]
    item.chmod(0o755)
    mode = calculate(); assert mode["digest"] != content["digest"]
    added = repo / "infra/azure/extra.tf"; added.write_text("extra\n")
    add = calculate(); assert add["digest"] != mode["digest"]
    added.rename(repo / "infra/azure/renamed.tf")
    rename = calculate(); assert rename["digest"] != add["digest"]
    (repo / "infra/azure/renamed.tf").unlink()
    removed = calculate(); assert removed["digest"] != rename["digest"]


def test_schema_example_contains_complete_identity_resource_and_attestation_shape() -> None:
    schema = json.loads((ROOT / "config/platform-bootstrap.schema.json").read_text())
    example = json.loads((ROOT / "config/platform-bootstrap.example.json").read_text())
    assert set(example) == set(schema["required"])
    assert len(example["identities"]["workloads"]) == 9
    assert example["identities"]["ui"] is None and example["identities"]["validator"] is None
    assert example["state"]["locked"] is True
    assert set(example["attestations"]) == {"providerQuotaCapacity", "albController", "migrationPolicy", "jitPermissions", "identityDenials"}


def test_bootstrap_dry_run_requires_exact_jit_scope_and_never_emits_manifest(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization = tmp_path / "authorization.json"
    authorization.write_text(json.dumps({
        "schemaVersion": 1, "activatedAt": (now-timedelta(minutes=5)).isoformat().replace("+00:00","Z"), "expiresAt": (now+timedelta(hours=1)).isoformat().replace("+00:00","Z"), "actorObjectId": "operator-1",
        "consentApprover": {"objectId": "security-approver-1", "role": "Privileged Role Administrator"},
        "roles": ["Application Administrator", "Contributor:application-rg", "Network Contributor:named-shared-network", "Private DNS Zone Contributor:named-zones", "ProviderQuotaRead:allowlisted", "Role Based Access Control Administrator:application-rg", "Storage Blob Data Contributor:state-container"],
        "denied": ["Global Administrator", "Owner", "GitHub Actions principal", "standing privilege", "unrelated app/data/resource access"],
    }))
    attestation = tmp_path / "attestation.json"
    attestation.write_text(json.dumps({"schemaVersion": 1, "capturedAt": (now-timedelta(minutes=5)).isoformat().replace("+00:00","Z"), "expiresAt": (now+timedelta(days=6)).isoformat().replace("+00:00","Z"), "providers": {}, "quotas": {}, "capacity": {}}))
    result = subprocess.run([str(BOOTSTRAP), "dry-run", "--repo-root", str(ROOT), "--authorization", str(authorization), "--attestation", str(attestation)], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "provider lock" in result.stdout
    assert not (ROOT / "config/platform-bootstrap-nonprod.json").exists()
    source = BOOTSTRAP.read_text() + (ROOT / "scripts/azure/bootstrap-data-principals.sh").read_text()
    assert "platform-bootstrap-nonprod.json" not in source


def test_finalization_is_the_only_emitter_and_is_t194_guarded() -> None:
    source = FINALIZE.read_text()
    assert "PLATFORM_FINALIZATION_AUTHORIZED" in source and "T194" in source
    assert 'config/platform-bootstrap-nonprod.json' in source
    assert "preflight-ui-platform.sh\" live" in source
    assert "now-captured > datetime.timedelta(days=7)" in source
    assert "validate-evidence.sh" in source
    denied = subprocess.run([str(FINALIZE)], cwd=ROOT, text=True, capture_output=True)
    assert denied.returncode != 0


def test_identityless_preflight_does_not_use_terraform_or_repair_resources() -> None:
    source = PREFLIGHT.read_text()
    schema_branch = source.split('[[ "$MODE" == schema-digest ]]', 1)[0]
    assert "terraform" not in schema_branch.lower()
    assert "az " not in schema_branch and "kubectl" not in schema_branch
    assert "terraform apply" not in source and "terraform import" not in source
    assert "az group create" not in source and "kubectl apply" not in source
    assert "get ingress --all-namespaces" in source
    assert "validatingadmissionpolicy core-migration-guardrails-v1" in source
    assert "validatingadmissionpolicybinding core-migration-guardrails-v1" in source
