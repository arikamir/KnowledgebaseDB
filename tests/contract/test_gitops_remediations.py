from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_release_bundle_schema_carries_provenance_and_evidence() -> None:
    schema = json.loads((ROOT / "config/gitops-release-bundle.schema.json").read_text())
    assert schema["properties"]["environment"] == {"const": "nonprod"}
    assert {
        "ciRun",
        "sourceTag",
        "sourceRevision",
        "validationEvidence",
    } <= set(schema["required"])
    assert set(schema["properties"]["services"]["required"]) == {"ui", "bff", "core"}


def test_evidence_schema_exposes_failure_diagnosis_and_automated_review_gate() -> None:
    schema = json.loads((ROOT / "config/gitops-evidence.schema.json").read_text())
    assert {
        "repository",
        "branch",
        "actorType",
        "eventType",
        "automatedReview",
        "validationEvidence",
        "readiness",
        "migration",
    } <= set(schema["required"])
    assert {"automationIdentity", "humanAction", "rollback"} <= set(schema["properties"])
    assert schema["properties"]["automatedReview"]["required"] == [
        "reviewer",
        "status",
        "statusCheck",
        "headRevision",
        "pullRequest",
        "proof",
        "observedAt",
    ]
    conditional_requirements = [
        clause["then"]["required"]
        for clause in schema["allOf"]
        if "then" in clause and "required" in clause["then"]
    ]
    assert ["automationIdentity"] in conditional_requirements
    assert ["humanAction"] in conditional_requirements
    assert ["rollback"] in conditional_requirements
    sync_properties = schema["properties"]["sync"]["properties"]
    assert {"affectedService", "reason", "nextAction"} <= set(sync_properties)
    timing_properties = schema["properties"]["timing"]["properties"]
    assert {"mergedAt", "diagnosedAt", "nextActionVisibleAt", "failureDiagnosisSeconds", "mergeToSyncSeconds"} <= set(timing_properties)
    failure_clause = next(
        clause["then"]
        for clause in schema["allOf"]
        if "properties" in clause.get("then", {})
    )
    assert {"affectedService", "reason", "nextAction"} <= set(
        failure_clause["properties"]["sync"]["required"]
    )
    assert {"failedAt", "diagnosedAt", "nextActionVisibleAt", "failureDiagnosisSeconds"} <= set(
        failure_clause["properties"]["timing"]["required"]
    )


def test_non_secret_entra_contract_requires_read_only_default_and_distinct_groups() -> None:
    contract = yaml.safe_load((ROOT / "config/argocd-oidc-rbac.yaml").read_text())
    data = contract["data"]
    assert data["defaultRole"] == "role:readonly"
    assert data["applicationReleaseGroup"] != data["infrastructureAdminGroup"]
    assert data["infrastructureAdminGroup"] != data["observabilityReadonlyGroup"]
    assert "secret" in data["oidcClientSecretRef"].lower()
    assert "clientSecret:" not in (ROOT / "config/argocd-oidc-rbac.yaml").read_text()


def test_release_bundle_validator_enforces_protected_source_and_digest_contract() -> None:
    bundle = ROOT / "tests/contract/fixtures/gitops/valid-release-bundle.json"
    env = os.environ.copy()
    env.update(
        {
            "REQUIRE_PROTECTED_TAG": "true",
            "GITHUB_REF_PROTECTED": "true",
            "GITHUB_SHA": "0123456789abcdef0123456789abcdef01234567",
        }
    )
    result = subprocess.run(
        [str(ROOT / "scripts/ci/validate-release-bundle.sh"), str(bundle)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_remediation_scripts_fail_closed_for_unprotected_tags() -> None:
    script = (ROOT / "scripts/ci/derive-release-version.sh").read_text()
    assert 'GITHUB_REF_PROTECTED:-false' in script
    assert "release tag is not proven protected" in script
    validator = (ROOT / "scripts/ci/validate-release-bundle.sh").read_text()
    assert "source tag is not proven protected" in validator


def test_entra_bootstrap_is_platform_owned_and_dry_run_by_default() -> None:
    script = (ROOT / "scripts/azure/apply-argocd-rbac.sh").read_text()
    assert 'APPLY:-false' in script
    assert "credential material is forbidden" in script
    assert "kubectl apply --server-side" in script


def test_delivery_workflow_only_starts_release_validation_from_v_tags() -> None:
    workflow = (ROOT / ".github/workflows/delivery.yml").read_text()
    assert "tags:" in workflow
    assert "- 'v*'" in workflow
    assert "verify-release-source:" in workflow
    assert "GITHUB_REF_PROTECTED" in workflow
    assert "scripts/ci/derive-release-version.sh" in workflow


def test_automated_review_helper_fails_closed_on_missing_or_stale_review() -> None:
    script = (ROOT / "scripts/ci/verify-ai-review.sh").read_text()
    assert "chatgpt-codex-connector[bot]" in script
    assert "AI_REVIEW_APPROVED_LOGINS" in script
    assert "--paginate --slurp" in script
    assert ".commit_id == $head" in script
    assert "ai-review-head:$head_sha" in script
    assert "review_request_id=" in script
    assert ".body == $body and .user.login == $requester" in script
    assert "candidate_request_id/reactions" in script
    assert '"CHANGES_REQUESTED"' in script
    assert '"DISMISSED"' in script
    assert '"no-findings-comment"' in script
    assert "reported current-head findings" in script
    assert "required automated review is missing or stale" in script
    assert "publish_status failure" in script
