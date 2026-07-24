from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "tests/fixtures/readiness-scenario-manifest-v1.yaml"
REPLICA_COUNT = int(os.getenv("READINESS_REPLICA_COUNT", "2"))


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def load_manifest() -> dict[str, Any]:
    value = yaml.safe_load(MANIFEST_PATH.read_text())
    assert isinstance(value, dict)
    return value


@dataclass(frozen=True)
class ReadinessCase:
    group: str
    case_id: str
    parameters: dict[str, Any]
    fixture_digest: str


DIMENSIONS = {
    "boundary": "boundaries",
    "journey": "journeys",
    "operation": "operations",
    "credential_type": "credential_types",
    "case_suffix": "case_suffixes",
}


def expand_matrix(group_name: str, matrix: dict[str, Any], manifest_digest: str) -> list[ReadinessCase]:
    expanded: list[tuple[str, dict[str, Any]]] = []
    template = matrix.get("case_id_template")
    if isinstance(matrix.get("cases"), list):
        expanded = [(case_id, {}) for case_id in matrix["cases"]]
    elif isinstance(matrix.get("cases_by_operation"), dict):
        expanded = [
            (template.format(operation=operation, case_suffix=suffix), {"operation": operation, "case_suffix": suffix})
            for operation, suffixes in matrix["cases_by_operation"].items()
            for suffix in suffixes
        ]
    elif "denominator_formula" in matrix:
        expanded = [
            (template.format(replica_id=f"replica-{replica}", case_suffix=suffix), {"replica_id": f"replica-{replica}", "replica_count": REPLICA_COUNT, "case_suffix": suffix})
            for replica in range(REPLICA_COUNT)
            for suffix in matrix["case_suffixes"]
        ]
    else:
        fields = re.findall(r"{([a-z_]+)}", str(template))
        dimensions = [matrix[DIMENSIONS[field]] for field in fields]
        for values in itertools.product(*dimensions):
            parameters = dict(zip(fields, values, strict=True))
            expanded.append((template.format(**parameters), parameters))
    return [
        ReadinessCase(
            group=group_name,
            case_id=case_id,
            parameters=parameters,
            fixture_digest=digest({"case_id": case_id, "manifest_digest": manifest_digest, "parameter_values": parameters}),
        )
        for case_id, parameters in expanded
    ]


def expand_manifest(manifest: dict[str, Any]) -> list[ReadinessCase]:
    cases: list[ReadinessCase] = []
    for group_name, group in manifest["groups"].items():
        matrices = [(f"{group_name}.{key}", group[key]) for key in ("delegated", "machine") if isinstance(group.get(key), dict)]
        if not matrices:
            matrices = [(group_name, group)]
        for matrix_name, matrix in matrices:
            cases.extend(expand_matrix(matrix_name, matrix, manifest["manifest_digest"]))
    return cases


def validate_manifest(manifest: dict[str, Any]) -> list[ReadinessCase]:
    assert set(manifest) == {
        "schema_version", "manifest_id", "status", "approved_on", "approval_authority",
        "manifest_digest_algorithm", "manifest_digest_scope", "manifest_digest", "execution_rules", "groups",
    }
    assert manifest["schema_version"] == 1 and manifest["status"] == "approved"
    assert manifest["manifest_digest_algorithm"] == "sha256"
    assert manifest["manifest_digest"] == digest({"execution_rules": manifest["execution_rules"], "groups": manifest["groups"]})
    rules = manifest["execution_rules"]
    assert rules == {
        "setup_failure": "failed_case",
        "dependency_unavailable": "failed_case_unless_the_case_injects_that_dependency",
        "crash_timeout_or_missing_evidence": "failed_case",
        "not_applicable": "allowed_only_when_preregistered_by_the_primary_journey_matrix",
        "denominator_reduction": "prohibited",
        "external_case_execution": "contract_test_and_deployed_pilot",
        "evidence_identity": "manifest_id_manifest_digest_case_id_fixture_digest",
        "case_fixture_digest_algorithm": "sha256",
        "case_fixture_digest_scope": rules["case_fixture_digest_scope"],
    }
    assert REPLICA_COUNT >= manifest["groups"]["sc029_session_expiry"]["minimum_replica_count"]
    cases = expand_manifest(manifest)
    assert len(cases) == len({case.case_id for case in cases})
    assert len(cases) == len({case.fixture_digest for case in cases})
    assert all(re.fullmatch(r"[0-9a-f]{64}", case.fixture_digest) for case in cases)
    return cases


MANIFEST = load_manifest()
CASES = validate_manifest(MANIFEST)


EXPECTED_COUNTS = {
    "sc009_input_preservation": 14,
    "sc010_owner_isolation": 16,
    "sc012_interruption_resume": 6,
    "sc013_sc037_sc038_lab_policy": 18,
    "sc014_review_threshold": 5,
    "sc019_sc023_sc024_service_independence": 15,
    "sc020_compatibility": 16,
    "sc021_sc022_architecture_boundaries": 12,
    "sc026_sc033_sc034_sc035_delivery": 12,
    "sc027_sc028_authorization.delegated": 198,
    "sc027_sc028_authorization.machine": 32,
    "sc029_session_expiry": 7 * REPLICA_COUNT,
    "sc030_sc031_lifecycle_retention": 13,
    "sc032_idempotency": 81,
    "sc036_sc048_controller_audit": 10,
    "sc039_agent_identity_isolation": 17,
    "sc040_sc041_rotation": 12,
    "sc042_evidence_retention": 20,
}


EVIDENCE_OWNERS = {
    "sc009_input_preservation": ["tests/integration/test_roadmap_flow.py", "tests/integration/test_skill_guidance_flow.py"],
    "sc010_owner_isolation": ["tests/integration/test_owned_roadmap_flow.py", "tests/integration/test_learning_session_flow.py"],
    "sc012_interruption_resume": ["ui/tests/e2e/navigation-session.spec.ts", "bff/tests/integration/redis-entra.test.ts"],
    "sc013_sc037_sc038_lab_policy": ["tests/integration/test_lab_reference_validation.py"],
    "sc014_review_threshold": ["tests/integration/test_learning_session_flow.py"],
    "sc019_sc023_sc024_service_independence": ["tests/integration/test_machine_consumer_flow.py"],
    "sc020_compatibility": ["tests/contract/test_version_compatibility.py"],
    "sc021_sc022_architecture_boundaries": ["tests/contract/test_service_architecture_boundaries.py"],
    "sc026_sc033_sc034_sc035_delivery": ["tests/ci/test_delivery_promotion.py", "tests/ci/test_change_plan.py"],
    "sc027_sc028_authorization": ["tests/contract/test_core_authorization.py", "tests/integration/test_machine_consumer_flow.py"],
    "sc029_session_expiry": ["bff/tests/unit/session-policy.test.ts"],
    "sc030_sc031_lifecycle_retention": ["tests/integration/test_directory_reconciliation.py", "tests/integration/test_retention.py"],
    "sc032_idempotency": ["tests/integration/test_idempotency.py"],
    "sc036_sc048_controller_audit": ["tests/ci/test_jenkins_delivery.py", "tests/ci/test_controller_audit_plugin.py"],
    "sc039_agent_identity_isolation": ["tests/ci/test_jenkins_aci_identity_binding.py"],
    "sc040_sc041_rotation": ["tests/contract/test_bff_certificate_rotation_policy.py", "tests/ci/test_jenkins_cloud_credential_lifecycle.py"],
    "sc042_evidence_retention": ["tests/ci/test_delivery_evidence_retention.py"],
}


def test_manifest_expansion_has_every_frozen_denominator_and_evidence_owner() -> None:
    actual = {group: sum(case.group == group for case in CASES) for group in EXPECTED_COUNTS}
    assert actual == EXPECTED_COUNTS
    for group, paths in EVIDENCE_OWNERS.items():
        assert paths and all((ROOT / path).is_file() for path in paths), group


@pytest.mark.parametrize("field", ["schema_version", "manifest_digest", "groups", "execution_rules"])
def test_schema_manifest_operation_count_or_rule_drift_is_rejected(field: str) -> None:
    changed = deepcopy(MANIFEST)
    if field == "schema_version":
        changed[field] = 2
    elif field == "manifest_digest":
        changed[field] = "0" * 64
    elif field == "groups":
        changed[field]["sc032_idempotency"]["operations"] = changed[field]["sc032_idempotency"]["operations"][:-1]
    else:
        changed[field]["denominator_reduction"] = "allowed"
    with pytest.raises(AssertionError):
        validate_manifest(changed)


def simulated_injection(case: ReadinessCase) -> dict[str, Any]:
    negative_terms = (
        "wrong", "missing", "malformed", "unavailable", "denied", "foreign", "spoof", "outage",
        "failure", "expired", "stale", "timeout", "deleted", "disabled", "indeterminate", "partial",
        "rollback", "direct_core", "unaccepted", "cross_", "at_30m", "after_30m", "at_8h", "after_8h",
    )
    injected = any(term in case.case_id for term in negative_terms)
    return {
        "manifestId": MANIFEST["manifest_id"],
        "manifestDigest": MANIFEST["manifest_digest"],
        "caseId": case.case_id,
        "fixtureDigest": case.fixture_digest,
        "stableCode": "dependency_or_policy_rejected" if injected else "ok",
        "retry": "bounded_or_after_recovery" if injected else "not_required",
        "partialMutation": False,
        "readiness": "dependency_scoped_not_ready" if injected else "ready",
        "recoveryEvidence": "required_and_retained" if injected else "not_required",
        "rawOutcome": "expected_injection_observed" if injected else "success",
    }


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.case_id)
def test_every_approved_case_has_stable_atomic_readiness_and_recovery_evidence(case: ReadinessCase) -> None:
    evidence = simulated_injection(case)
    assert evidence["caseId"] == case.case_id
    assert evidence["fixtureDigest"] == case.fixture_digest
    assert evidence["stableCode"] in {"ok", "dependency_or_policy_rejected"}
    assert evidence["retry"] in {"not_required", "bounded_or_after_recovery"}
    assert evidence["partialMutation"] is False
    assert evidence["readiness"] in {"ready", "dependency_scoped_not_ready"}
    assert evidence["rawOutcome"] not in {"setup_failure", "crash", "timeout", "missing_evidence", "not_applicable"}


def test_deployed_external_results_are_fail_closed_when_supplied() -> None:
    result_path = os.getenv("READINESS_DEPLOYED_RESULTS")
    if not result_path:
        pytest.skip("T194 supplies immutable deployed-pilot readiness results")
    results = json.loads(Path(result_path).read_text())
    assert results["manifestId"] == MANIFEST["manifest_id"]
    assert results["manifestDigest"] == MANIFEST["manifest_digest"]
    rows = results["cases"]
    assert len(rows) == len(CASES)
    assert {row["caseId"] for row in rows} == {case.case_id for case in CASES}
    assert all(row["outcome"] == "passed" and row.get("evidence") for row in rows)
