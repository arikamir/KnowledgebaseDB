#!/usr/bin/env python3
"""Deterministic validation for the feature's authoritative contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FEATURE = ROOT / "specs/003-develop-ui"
BFF_CONTRACT = FEATURE / "contracts/bff-api-v1.openapi.yaml"
CORE_CONTRACT = FEATURE / "contracts/core-api-v1.openapi.yaml"
READINESS = ROOT / "tests/fixtures/readiness-scenario-manifest-v1.yaml"
PERFORMANCE = ROOT / "tests/performance/performance-profile-v1.json"
INTERACTION = ROOT / "tests/performance/interaction-performance-profile-v1.json"
INTERACTION_FIXTURES = ROOT / "tests/performance/interaction-performance-fixtures-v1.json"
CATALOG = FEATURE / "contracts/supported-guidance-topics-v1.yaml"
FOUNDATION_TEST_MANIFEST = ROOT / "config/us1-foundation-test-manifest-v1.txt"
FOUNDATION_RUNNER = ROOT / "scripts/ci/validate-us1-foundation.sh"


class ContractGateError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractGateError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path}: top level must be an object")
    return value


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path}: top level must be a mapping")
    return value


@dataclass(frozen=True)
class OpenApiSummary:
    path: Path
    digest: str
    operation_ids: frozenset[str]


def validate_openapi(path: Path) -> OpenApiSummary:
    document = load_yaml(path)
    require(str(document.get("openapi", "")).startswith("3."), f"{path}: OpenAPI 3 required")
    require(isinstance(document.get("paths"), dict) and document["paths"], f"{path}: paths required")
    require(isinstance(document.get("components", {}).get("schemas"), dict), f"{path}: schemas required")
    operation_ids: list[str] = []
    for route, path_item in document["paths"].items():
        require(str(route).startswith("/"), f"{path}: invalid route {route!r}")
        require(isinstance(path_item, dict), f"{path}: invalid path item {route}")
        for method, operation in path_item.items():
            if method.lower() not in {"get", "put", "post", "delete", "patch", "options", "head", "trace"}:
                continue
            require(isinstance(operation, dict), f"{path}: invalid {method} {route}")
            operation_id = operation.get("operationId")
            require(isinstance(operation_id, str) and operation_id, f"{path}: operationId missing at {method} {route}")
            require(isinstance(operation.get("responses"), dict) and operation["responses"], f"{path}: responses missing for {operation_id}")
            operation_ids.append(operation_id)
    require(len(operation_ids) == len(set(operation_ids)), f"{path}: duplicate operationId")
    return OpenApiSummary(path, sha256_file(path), frozenset(operation_ids))


def validate_profile_digest(profile: dict[str, Any], path: Path) -> None:
    declared = profile.get("profileDigest")
    without_digest = dict(profile)
    without_digest.pop("profileDigest", None)
    require(declared == sha256_bytes(canonical_json(without_digest)), f"{path}: profileDigest mismatch")


def validate_contract_bindings(profile: dict[str, Any], summaries: Iterable[OpenApiSummary], path: Path) -> None:
    by_path = {str(summary.path.relative_to(ROOT)): summary for summary in summaries}
    bindings = profile.get("contractBindings", {})
    for name in ("bffContract", "coreContract"):
        binding = bindings.get(name)
        require(isinstance(binding, dict), f"{path}: missing {name}")
        bound_path = binding.get("path")
        require(bound_path in by_path, f"{path}: unknown bound contract {bound_path!r}")
        require(binding.get("digest") == by_path[bound_path].digest, f"{path}: {name} digest mismatch")


def validate_performance_profile(summaries: Iterable[OpenApiSummary]) -> None:
    profile = load_json(PERFORMANCE)
    validate_profile_digest(profile, PERFORMANCE)
    validate_contract_bindings(profile, summaries, PERFORMANCE)
    fixtures = profile.get("fixtures")
    require(isinstance(fixtures, list) and len(fixtures) == 6, f"{PERFORMANCE}: six fixtures required")
    require(profile.get("fixtureDigest") == sha256_bytes(canonical_json(fixtures)), f"{PERFORMANCE}: fixtureDigest mismatch")
    execution = profile.get("execution", {})
    require(execution.get("workersPerScenario") == 10, f"{PERFORMANCE}: workers must be 10")
    require(execution.get("measuredRequestsPerWorker") == 10, f"{PERFORMANCE}: measured requests must be 10")
    require(execution.get("measuredAttemptsPerScenario") == 100, f"{PERFORMANCE}: denominator must be 100")
    scenarios = execution.get("scenarioOperations", {})
    bff_ops, core_ops = [summary.operation_ids for summary in summaries]
    for scenario, pairing in scenarios.items():
        require(pairing.get("fixtureOperationId") in bff_ops, f"{PERFORMANCE}: unknown BFF operation for {scenario}")
        require(pairing.get("coreOperationId") in core_ops, f"{PERFORMANCE}: unknown core operation for {scenario}")


def validate_interaction_profile(summaries: Iterable[OpenApiSummary]) -> None:
    profile = load_json(INTERACTION)
    fixtures = load_json(INTERACTION_FIXTURES)
    validate_profile_digest(profile, INTERACTION)
    validate_contract_bindings(profile, summaries, INTERACTION)
    fixture_digest = sha256_file(INTERACTION_FIXTURES)
    require(profile.get("fixtureDigest") == fixture_digest, f"{INTERACTION}: fixtureDigest mismatch")
    require(profile.get("fixtureSet", {}).get("digest") == fixture_digest, f"{INTERACTION}: fixtureSet digest mismatch")
    execution = profile.get("execution", {})
    require(execution.get("derivedInputDigestAlgorithm") == "sha256", f"{INTERACTION}: derived digest algorithm")
    required_fields = execution.get("derivedInputDigestObject", {}).get("requiredFieldsInOrderForReviewOnly")
    require(required_fields == [
        "profileId", "fixtureSetId", "caseId", "scenario", "phase", "workerIndex",
        "requestOrdinal", "operationId", "materializedState", "materializedRequest", "providerResult",
    ], f"{INTERACTION}: derived-input field contract drift")
    scenarios = execution.get("scenarios", {})
    fixture_map = fixtures.get("fixtures", {})
    required_keys = profile.get("fixtureSet", {}).get("requiredFixtureKeys")
    require(sorted(scenarios) == sorted(fixture_map) == sorted(required_keys), f"{INTERACTION}: fixture/scenario mismatch")
    case_ids = [value.get("caseId") for value in fixture_map.values()]
    require(all(isinstance(value, str) and value for value in case_ids) and len(case_ids) == len(set(case_ids)), f"{INTERACTION_FIXTURES}: unique case IDs required")
    grammar = fixtures.get("derivation", {}).get("placeholderGrammar", {})
    require(set(grammar) == {"${constant:name}", "${uuidv5:field}", "${token:field}", "${time:field}", "${template:path}"}, f"{INTERACTION_FIXTURES}: placeholder grammar drift")
    require(fixtures.get("derivation", {}).get("workerIndexRange") == [0, 9], f"{INTERACTION_FIXTURES}: worker range")
    require(fixtures.get("derivation", {}).get("measuredRequestOrdinalRange") == [0, 9], f"{INTERACTION_FIXTURES}: ordinal range")
    placeholders = re.findall(r"\$\{([^}]+)\}", json.dumps(fixture_map, ensure_ascii=False))
    require(all(value.split(":", 1)[0] in {"constant", "uuidv5", "token", "time", "template"} for value in placeholders), f"{INTERACTION_FIXTURES}: unresolved placeholder class")
    for scenario, fixture in fixture_map.items():
        require(fixture.get("operationId") == scenarios[scenario].get("operationId"), f"{INTERACTION_FIXTURES}: operation mismatch for {scenario}")
        require((ROOT / fixture.get("contractPath", "")).is_file(), f"{INTERACTION_FIXTURES}: missing contract binding for {scenario}")
    all_operations = set().union(*(summary.operation_ids for summary in summaries))
    require(all(value.get("operationId") in all_operations for value in scenarios.values()), f"{INTERACTION}: unknown operation")
    callback = scenarios.get("authentication_callback", {})
    require(callback.get("providerMode") == "approved_deterministic_in_process_fixture", f"{INTERACTION}: callback provider mode")
    require("after the approved provider fixture" in callback.get("timingStart", ""), f"{INTERACTION}: callback boundary")
    vectors = fixtures.get("knownAnswerVectors")
    require(isinstance(vectors, list) and len(vectors) == 2, f"{INTERACTION_FIXTURES}: two vectors required")
    for vector in vectors:
        actual = sha256_bytes(canonical_json(vector.get("derivedInputObject")))
        require(actual == vector.get("expectedSha256"), f"{INTERACTION_FIXTURES}: vector {vector.get('vectorId')} mismatch")
    evidence = profile.get("requiredEvidenceFields", [])
    for field in ("derivedInputDigest", "profileDigest", "fixtureDigest", "providerMode", "rawOutcome"):
        require(field in evidence, f"{INTERACTION}: missing evidence field {field}")


def _expanded_group_count(group: dict[str, Any]) -> int:
    if isinstance(group.get("cases"), list):
        return len(group["cases"])
    if isinstance(group.get("cases_by_operation"), dict):
        cases = group["cases_by_operation"]
        expected = group.get("denominator_per_operation")
        require(all(len(values) == expected for values in cases.values()), "per-operation case count drift")
        return sum(len(values) for values in cases.values())
    dimensions = [
        value
        for key, value in group.items()
        if key not in {"criteria", "expectations", "case_id_template", "denominator", "expanded_denominator", "denominator_per_operation"}
        and isinstance(value, list)
    ]
    count = 1
    for values in dimensions:
        count *= len(values)
    return count


def validate_readiness_manifest() -> None:
    manifest = load_yaml(READINESS)
    digest_input = {"execution_rules": manifest.get("execution_rules"), "groups": manifest.get("groups")}
    require(manifest.get("manifest_digest") == sha256_bytes(canonical_json(digest_input)), f"{READINESS}: digest mismatch")
    groups = manifest.get("groups")
    require(isinstance(groups, dict) and groups, f"{READINESS}: groups required")
    for name, group in groups.items():
        require(isinstance(group, dict), f"{READINESS}: invalid group {name}")
        nested_matrices = [group[key] for key in ("delegated", "machine") if isinstance(group.get(key), dict)]
        if nested_matrices:
            for matrix in nested_matrices:
                actual = _expanded_group_count(matrix)
                require(matrix.get("expanded_denominator") == actual, f"{READINESS}: {name} nested denominator")
                if "denominator_per_operation" in matrix and "case_suffixes" in matrix:
                    require(matrix["denominator_per_operation"] == len(matrix["case_suffixes"]), f"{READINESS}: {name} nested per-operation denominator")
            continue
        if "denominator_formula" in group:
            require(
                str(len(group.get("case_suffixes", []))) in str(group["denominator_formula"]),
                f"{READINESS}: {name} denominator formula does not match suffix count",
            )
            require(group.get("minimum_replica_count", 0) >= 1, f"{READINESS}: {name} minimum replica count")
            continue
        actual = _expanded_group_count(group)
        declared = group.get("expanded_denominator", group.get("denominator"))
        require(declared == actual, f"{READINESS}: {name} denominator {declared!r} != {actual}")
        if "denominator_per_operation" in group:
            operations = group.get("operations", [])
            suffixes = group.get("case_suffixes", [])
            require(group["denominator_per_operation"] == len(suffixes), f"{READINESS}: {name} per-operation denominator")
            require(actual == len(operations) * len(suffixes), f"{READINESS}: {name} operation expansion")

    case_digests: set[str] = set()
    for group_name, group in groups.items():
        matrices = [group[key] for key in ("delegated", "machine") if isinstance(group.get(key), dict)] or [group]
        for matrix in matrices:
            cases: list[tuple[str, dict[str, Any]]] = []
            if isinstance(matrix.get("cases"), list):
                cases = [(case_id, {}) for case_id in matrix["cases"]]
            elif isinstance(matrix.get("cases_by_operation"), dict):
                cases = [
                    (matrix["case_id_template"].format(operation=operation, case_suffix=suffix), {"operation": operation, "case_suffix": suffix})
                    for operation, suffixes in matrix["cases_by_operation"].items() for suffix in suffixes
                ]
            elif isinstance(matrix.get("operations"), list) and isinstance(matrix.get("case_suffixes"), list):
                cases = [
                    (matrix["case_id_template"].format(operation=operation, case_suffix=suffix), {"operation": operation, "case_suffix": suffix})
                    for operation in matrix["operations"] for suffix in matrix["case_suffixes"]
                ]
            for case_id, parameters in cases:
                payload = {"case_id": case_id, "manifest_digest": manifest["manifest_digest"], "parameter_values": parameters}
                case_digest = sha256_bytes(canonical_json(payload))
                require(case_digest not in case_digests, f"{READINESS}: duplicate derived case digest in {group_name}")
                case_digests.add(case_digest)
    require(len(case_digests) >= 300 and all(re.fullmatch(r"[a-f0-9]{64}", value) for value in case_digests), f"{READINESS}: derived case digest coverage")


def validate_foundation_runner() -> None:
    require(FOUNDATION_TEST_MANIFEST.is_file() and FOUNDATION_RUNNER.is_file(), "US1 foundation runner artifacts missing")
    paths = [line.strip() for line in FOUNDATION_TEST_MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(paths == sorted(set(paths)), "US1 foundation manifest must be sorted and duplicate-free")
    require(all(not any(character in path for character in "*?[") for path in paths), "US1 foundation manifest prohibits globs")
    require(all((ROOT / path).is_file() for path in paths), "US1 foundation manifest must contain exact existing files")
    required = {
        "ui/tests/unit/persistence-state.test.ts", "ui/tests/e2e/persistence-status.spec.ts",
        "ui/tests/e2e/navigation-session.spec.ts", "tests/integration/test_postgres_entra.py",
        "tests/unit/test_next_action_foundation.py", "bff/tests/integration/redis-entra.test.ts",
    }
    require(required.issubset(paths), "US1 foundation manifest missing required owner tests")
    runner = FOUNDATION_RUNNER.read_text(encoding="utf-8")
    for command in ("validate-api-contracts.sh", "generate_contracts.py --check", "run typecheck", "playwright test"):
        require(command in runner, f"US1 foundation runner missing {command}")


def validate_generated_drift() -> None:
    from scripts.ci.generate_contracts import generated_files

    for path, expected in generated_files().items():
        require(path.is_file() and path.read_text(encoding="utf-8") == expected, f"generated contract drift: {path.relative_to(ROOT)}")


def validate_catalog() -> None:
    catalog = load_yaml(CATALOG)
    require(catalog.get("schema_version") == 1, f"{CATALOG}: schema_version")
    topics = catalog.get("topics")
    require(isinstance(topics, list) and topics, f"{CATALOG}: topics required")
    ids = [topic.get("id") for topic in topics]
    require(len(ids) == len(set(ids)), f"{CATALOG}: duplicate topic ID")
    source_path = ROOT / str(catalog.get("source_snapshot"))
    source_topics = json.loads(source_path.read_text(encoding="utf-8"))
    require(
        [topic.get("name") for topic in topics] == [topic.get("name") for topic in source_topics],
        f"{CATALOG}: topic order must match its source snapshot",
    )
    for topic in topics:
        require(topic.get("status") in {"active", "unavailable", "retired"}, f"{CATALOG}: invalid status")
        aliases = topic.get("aliases", [])
        require(len(aliases) == len(set(alias.casefold() for alias in aliases)), f"{CATALOG}: duplicate aliases")


def validate_traceability() -> None:
    spec_text = (FEATURE / "spec.md").read_text(encoding="utf-8")
    task_text = (FEATURE / "tasks.md").read_text(encoding="utf-8")
    trace_text = (FEATURE / "requirements-traceability.md").read_text(encoding="utf-8")
    requirements = re.findall(r"^- \*\*((?:FR|SC)-\d{3})\*\*:", spec_text, re.MULTILINE)
    expected = [f"FR-{value:03d}" for value in range(1, 76)] + [f"SC-{value:03d}" for value in range(1, 51)]
    require(requirements == expected, "spec requirement sequence must be FR-001..075 then SC-001..050")
    tasks = re.findall(r"^- \[[ xX]\] (T\d{3})\b", task_text, re.MULTILINE)
    require(tasks == [f"T{value:03d}" for value in range(1, 199)], "task sequence must be T001..T198")
    rows = [line for line in trace_text.splitlines() if re.match(r"^\| (?:FR|SC)-\d{3} \|", line)]
    row_ids = [line.split("|")[1].strip() for line in rows]
    require(row_ids == expected, "traceability rows must exactly match requirement order")
    referenced = set(re.findall(r"T\d{3}", "\n".join(rows)))
    require(referenced == set(tasks), "traceability must reference every task and no unknown task")
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        require(len(cells) == 6 and all(cells), f"empty or malformed traceability row: {cells[:1]}")


def validate_all(write_digests: bool = False) -> dict[str, str]:
    bff = validate_openapi(BFF_CONTRACT)
    core = validate_openapi(CORE_CONTRACT)
    summaries = (bff, core)
    validate_performance_profile(summaries)
    validate_interaction_profile(summaries)
    validate_readiness_manifest()
    validate_catalog()
    validate_traceability()
    validate_foundation_runner()
    validate_generated_drift()
    digests = {"bff-api-v1": bff.digest, "core-api-v1": core.digest}
    if write_digests:
        for name, digest in digests.items():
            (FEATURE / f"contracts/{name}.digest").write_text(f"{digest}\n", encoding="utf-8")
    return digests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-digests", action="store_true")
    args = parser.parse_args()
    try:
        digests = validate_all(write_digests=args.write_digests)
    except (ContractGateError, KeyError, TypeError, ValueError, yaml.YAMLError, json.JSONDecodeError) as error:
        print(f"contract gate failed: {error}")
        return 1
    print(json.dumps({"status": "pass", "digests": digests}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
