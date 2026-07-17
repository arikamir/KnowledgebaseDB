from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable
import uuid

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
LEGACY_PATH = ROOT / "tests/performance/performance-profile-v1.json"
INTERACTION_PATH = ROOT / "tests/performance/interaction-performance-profile-v1.json"
FIXTURES_PATH = ROOT / "tests/performance/interaction-performance-fixtures-v1.json"
MAPPER_PATHS = (ROOT / "bff/src/contracts/roadmap.ts", ROOT / "bff/src/contracts/guidance.ts")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    assert isinstance(value, dict)
    return value


LEGACY = load(LEGACY_PATH)
INTERACTION = load(INTERACTION_PATH)
FIXTURE_SET = load(FIXTURES_PATH)


def validate_profile(profile: dict[str, Any], path: Path) -> None:
    without_digest = dict(profile)
    declared = without_digest.pop("profileDigest")
    assert declared == sha(canonical(without_digest)), path
    for binding in ("bffContract", "coreContract"):
        item = profile["contractBindings"][binding]
        assert sha((ROOT / item["path"]).read_bytes()) == item["digest"]
    assert profile["execution"]["workersPerScenario"] == 10
    assert profile["execution"]["warmupRequestsPerWorker"] == 2
    assert profile["execution"]["measuredRequestsPerWorker"] == 10
    assert profile["execution"]["measuredAttemptsPerScenario"] == 100
    assert profile["execution"]["requiredThresholdPassesPerScenario"] == 95


@lru_cache(maxsize=None)
def operation(contract_path: str, operation_id: str) -> tuple[str, str, dict[str, Any]]:
    contract = yaml.safe_load((ROOT / contract_path).read_text())
    matches = [
        (method.upper(), route, spec)
        for route, path_item in contract["paths"].items()
        for method, spec in path_item.items()
        if isinstance(spec, dict) and spec.get("operationId") == operation_id
    ]
    assert len(matches) == 1
    return matches[0]


def test_profiles_fixture_bytes_contracts_operations_mapper_and_evidence_are_frozen() -> None:
    validate_profile(LEGACY, LEGACY_PATH)
    validate_profile(INTERACTION, INTERACTION_PATH)
    assert LEGACY["fixtureDigest"] == sha(canonical(LEGACY["fixtures"]))
    exact_fixture_digest = sha(FIXTURES_PATH.read_bytes())
    assert INTERACTION["fixtureDigest"] == INTERACTION["fixtureSet"]["digest"] == exact_fixture_digest
    assert sorted(INTERACTION["execution"]["scenarios"]) == sorted(FIXTURE_SET["fixtures"])
    for scenario, binding in LEGACY["execution"]["scenarioOperations"].items():
        assert operation(LEGACY["execution"]["fixtureRequestContract"], binding["fixtureOperationId"])[0] == "POST"
        assert operation(LEGACY["execution"]["coreRequestContract"], binding["coreOperationId"])[0] == "POST"
        assert scenario in {"roadmap", "guidance"}
    for scenario, binding in INTERACTION["execution"]["scenarios"].items():
        fixture = FIXTURE_SET["fixtures"][scenario]
        method, _, _ = operation(fixture["contractPath"], binding["operationId"])
        assert method == fixture["method"]
    mapper_digest = sha(b"\0".join(path.read_bytes() for path in MAPPER_PATHS))
    assert re.fullmatch(r"[0-9a-f]{64}", mapper_digest)
    required = set(INTERACTION["requiredEvidenceFields"])
    assert {"derivedInputDigest", "profileDigest", "fixtureDigest", "providerMode", "timingStartBoundary", "timingStopBoundary", "rawOutcome"} <= required


def test_any_profile_fixture_operation_provider_boundary_or_timeout_drift_fails_closed() -> None:
    changes = []
    for field, value in (("workersPerScenario", 9), ("hardTimeoutMs", 5001)):
        changed = deepcopy(INTERACTION)
        changed["execution"][field] = value
        changes.append(changed)
    changed = deepcopy(INTERACTION)
    changed["execution"]["scenarios"]["authentication_callback"]["providerMode"] = "live"
    changes.append(changed)
    changed = deepcopy(INTERACTION)
    changed["execution"]["scenarios"]["bff_logout"]["operationId"] = "unknown"
    changes.append(changed)
    for changed in changes:
        with pytest.raises(AssertionError):
            validate_profile(changed, INTERACTION_PATH)


TOKEN = re.compile(r"\$\{(constant|uuidv5|token|time|template):([^}]+)}")
NAMESPACE = uuid.UUID(FIXTURE_SET["derivation"]["uuidNamespace"])
EPOCH = datetime.fromisoformat(FIXTURE_SET["derivation"]["clockEpoch"].replace("Z", "+00:00"))


def name(scenario: str, phase: str, worker: int, ordinal: int, field: str) -> str:
    return f"interaction-performance-profile-v1:{scenario}:{phase}:{worker}:{ordinal}:{field}"


def timestamp(field: str, worker: int, ordinal: int) -> str:
    issued = EPOCH + timedelta(minutes=worker, seconds=ordinal)
    value = {"issuedAt": issued, "idleExpiresAt": issued + timedelta(minutes=30), "absoluteExpiresAt": issued + timedelta(hours=8)}[field]
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def raw_template(path: str) -> Any:
    value: Any = FIXTURE_SET["fixtures"]
    for part in path.split("."):
        value = value[part]
    return deepcopy(value)


def resolve(value: Any, scenario: str, phase: str, worker: int, ordinal: int) -> Any:
    if isinstance(value, dict):
        return {key: resolve(item, scenario, phase, worker, ordinal) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, scenario, phase, worker, ordinal) for item in value]
    if not isinstance(value, str):
        return value
    exact = TOKEN.fullmatch(value)
    if exact and exact.group(1) == "constant":
        return deepcopy(FIXTURE_SET["constants"][exact.group(2)])
    if exact and exact.group(1) == "template":
        return resolve(raw_template(exact.group(2)), scenario, phase, worker, ordinal)

    def replace(match: re.Match[str]) -> str:
        kind, field = match.groups()
        fixture_name = name(scenario, phase, worker, ordinal, field)
        if kind == "constant":
            result = FIXTURE_SET["constants"][field]
            assert isinstance(result, str)
            return result
        if kind == "uuidv5":
            return str(uuid.uuid5(NAMESPACE, fixture_name))
        if kind == "token":
            return (f"sc050-{field}-" + sha(fixture_name.encode()))[:64]
        if kind == "time":
            return timestamp(field, worker, ordinal)
        if kind == "template":
            result = resolve(raw_template(field), scenario, phase, worker, ordinal)
            assert isinstance(result, str)
            return result
        raise AssertionError(kind)

    resolved = TOKEN.sub(replace, value)
    assert "${" not in resolved
    return resolved


def assign_override(value: Any, path: str, replacement: Any) -> None:
    parts = re.findall(r"([^.\[\]]+)|\[(\d+)]", path)
    target = value
    tokens: list[str | int] = [int(index) if index else key for key, index in parts]
    for token in tokens[:-1]:
        target = target[token]
    target[tokens[-1]] = replacement


def seed_state(scenario: str, phase: str, worker: int, ordinal: int) -> Any:
    fixture = FIXTURE_SET["fixtures"][scenario]
    if "seedState" in fixture:
        state = resolve(fixture["seedState"], scenario, phase, worker, ordinal)
    else:
        reference = fixture["seedStateRef"]
        state = resolve(FIXTURE_SET["fixtures"][reference]["seedState"], scenario, phase, worker, ordinal)
    for path, value in fixture.get("seedOverrides", {}).items():
        assign_override(state, path, resolve(value, scenario, phase, worker, ordinal))
    return state


def materialize(scenario: str, phase: str, worker: int, ordinal: int) -> dict[str, Any]:
    fixture = FIXTURE_SET["fixtures"][scenario]
    request = {
        "method": fixture["method"],
        "pathAndQuery": resolve(fixture["pathTemplate"], scenario, phase, worker, ordinal),
        "headers": resolve(fixture["headers"], scenario, phase, worker, ordinal),
        "body": resolve(fixture["body"], scenario, phase, worker, ordinal),
    }
    method, route, _ = operation(fixture["contractPath"], fixture["operationId"])
    assert request["method"] == method
    path_only = request["pathAndQuery"].split("?", 1)[0]
    route_pattern = re.sub(r"{[^}]+}", r"[^/]+", route)
    contract_relative_path = re.sub(r"^/(?:bff|api)/v1", "", path_only)
    assert re.fullmatch(route_pattern, contract_relative_path)
    provider = resolve(fixture.get("providerResult"), scenario, phase, worker, ordinal)
    derived = {
        "profileId": INTERACTION["profileId"],
        "fixtureSetId": FIXTURE_SET["fixtureSetId"],
        "caseId": fixture["caseId"],
        "scenario": scenario,
        "phase": phase,
        "workerIndex": worker,
        "requestOrdinal": ordinal,
        "operationId": fixture["operationId"],
        "materializedState": seed_state(scenario, phase, worker, ordinal),
        "materializedRequest": request,
        "providerResult": provider,
    }
    return {"derived": derived, "digest": sha(canonical(derived))}


def test_known_answers_and_all_sc050_inputs_are_exactly_deterministic() -> None:
    for vector in FIXTURE_SET["knownAnswerVectors"]:
        assert sha(canonical(vector["derivedInputObject"])) == vector["expectedSha256"]
        scenario = vector["derivedInputObject"]["scenario"]
        generated = materialize(scenario, vector["derivedInputObject"]["phase"], vector["derivedInputObject"]["workerIndex"], vector["derivedInputObject"]["requestOrdinal"])
        assert generated["derived"] == vector["derivedInputObject"]
        assert generated["digest"] == vector["expectedSha256"]
    values = [materialize(scenario, "measured", worker, ordinal) for scenario in sorted(FIXTURE_SET["fixtures"]) for worker in range(10) for ordinal in range(10)]
    assert len(values) == 800
    assert len({value["digest"] for value in values}) == 800


def measured_call(payload: dict[str, Any], provider_mode: str) -> tuple[float, str]:
    # Timing starts only after fixture materialization/provider return and uses
    # the monotonic boundary owned by this in-process callback.
    if payload["scenario"] == "authentication_callback":
        assert provider_mode == "approved_deterministic_in_process_fixture"
        assert payload["providerResult"] is not None
    else:
        assert provider_mode == "not_applicable" and payload["providerResult"] is None
    started = time.perf_counter_ns()
    canonical(payload)
    duration = (time.perf_counter_ns() - started) / 1_000_000
    return duration, "success"


def concurrent_profile(
    scenarios: list[str], timeout_ms: Callable[[str], int], threshold_ms: Callable[[str], int],
    payload: Callable[[str, str, int, int], tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    results: dict[str, list[dict[str, Any]]] = {}
    for scenario in scenarios:
        observations: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=10) as pool:
            for phase, ordinals in (("warmup", range(2)), ("measured", range(10))):
                for ordinal in ordinals:
                    barrier = threading.Barrier(10)

                    def invoke(worker: int) -> dict[str, Any]:
                        derived, adjacent = payload(scenario, phase, worker, ordinal)
                        barrier.wait(timeout=5)
                        provider_mode = adjacent["providerMode"]
                        duration, outcome = measured_call(derived, provider_mode)
                        return adjacent | {"workerIndex": worker, "requestOrdinal": ordinal, "monotonicDurationMs": duration, "rawOutcome": outcome}

                    futures = [pool.submit(invoke, worker) for worker in range(10)]
                    for future in futures:
                        try:
                            row = future.result(timeout=timeout_ms(scenario) / 1000)
                        except FutureTimeout:
                            row = {"monotonicDurationMs": float(timeout_ms(scenario)), "rawOutcome": "timeout", "timeoutApplied": True}
                        if phase == "warmup":
                            assert row["rawOutcome"] == "success" and row["monotonicDurationMs"] < timeout_ms(scenario)
                        else:
                            row["thresholdPassed"] = row["rawOutcome"] == "success" and row["monotonicDurationMs"] <= threshold_ms(scenario)
                            observations.append(row)
        assert len(observations) == 100
        values = sorted(row["monotonicDurationMs"] for row in observations)
        p95 = values[math.ceil(0.95 * len(values)) - 1]
        assert sum(row["thresholdPassed"] for row in observations) >= 95
        for row in observations:
            row["percentileValueMs"] = row["monotonicDurationMs"]
            row["calculatedNearestRankP95Ms"] = p95
        results[scenario] = observations
    return results


def test_sc043_exact_assignment_barriers_warmups_denominator_timeout_and_p95() -> None:
    execution = LEGACY["execution"]
    fixtures = {scenario: sorted((item for item in LEGACY["fixtures"] if item["scenario"] == scenario), key=lambda item: item["caseId"]) for scenario in execution["scenarios"]}
    mapper_digest = sha(b"\0".join(path.read_bytes() for path in MAPPER_PATHS))

    def payload(scenario: str, phase: str, worker: int, ordinal: int) -> tuple[dict[str, Any], dict[str, Any]]:
        fixture = fixtures[scenario][(worker + ordinal) % 3]
        return ({"scenario": scenario, "providerResult": None, "request": fixture["request"]}, {
            "profileId": LEGACY["profileId"], "profileDigest": LEGACY["profileDigest"], "fixtureDigest": LEGACY["fixtureDigest"],
            "bffContractDigest": LEGACY["contractBindings"]["bffContract"]["digest"], "coreContractDigest": LEGACY["contractBindings"]["coreContract"]["digest"],
            "mapperDigest": mapper_digest, "caseId": fixture["caseId"], "scenario": scenario, "providerMode": "not_applicable",
            "environment": "deterministic-in-process", "coreImageDigest": "not_applicable",
        })

    rows = concurrent_profile(
        execution["scenarios"],
        lambda scenario: execution[f"{scenario}RequestTimeoutMs"],
        lambda scenario: execution[f"{scenario}ThresholdMs"],
        payload,
    )
    assert {scenario: len(values) for scenario, values in rows.items()} == {"roadmap": 100, "guidance": 100}
    assert {row["caseId"] for values in rows.values() for row in values} == {fixture["caseId"] for fixture in LEGACY["fixtures"]}
    assert all(set(LEGACY["requiredEvidenceFields"]) <= set(row) for values in rows.values() for row in values)


def test_sc050_all_eight_scenarios_use_approved_provider_fixture_and_exact_evidence() -> None:
    execution = INTERACTION["execution"]

    def payload(scenario: str, phase: str, worker: int, ordinal: int) -> tuple[dict[str, Any], dict[str, Any]]:
        generated = materialize(scenario, phase, worker, ordinal)
        binding = execution["scenarios"][scenario]
        provider_mode = binding.get("providerMode", "not_applicable")
        return generated["derived"], {
            "profileId": INTERACTION["profileId"], "profileDigest": INTERACTION["profileDigest"], "fixtureDigest": INTERACTION["fixtureDigest"],
            "fixtureSetPath": INTERACTION["fixtureSet"]["path"], "fixtureKey": scenario, "derivedInputDigest": generated["digest"],
            "bffContractDigest": INTERACTION["contractBindings"]["bffContract"]["digest"], "coreContractDigest": INTERACTION["contractBindings"]["coreContract"]["digest"],
            "caseId": generated["derived"]["caseId"], "scenario": scenario, "operationId": binding["operationId"], "providerMode": provider_mode,
            "environment": "deterministic-in-process", "bffImageDigest": "not_applicable", "coreImageDigest": "not_applicable",
            "timingStartBoundary": binding["timingStart"], "timingStopBoundary": binding["timingStop"], "timeoutApplied": False,
        }

    rows = concurrent_profile(
        sorted(execution["scenarios"]), lambda _: execution["hardTimeoutMs"], lambda _: execution["thresholdMs"], payload
    )
    assert len(rows) == 8 and all(len(values) == 100 for values in rows.values())
    assert all(set(INTERACTION["requiredEvidenceFields"]) <= set(row) for values in rows.values() for row in values)
    callback = rows["authentication_callback"]
    assert all(row["providerMode"] == "approved_deterministic_in_process_fixture" for row in callback)
    assert all(row["providerMode"] == "not_applicable" for scenario, values in rows.items() if scenario != "authentication_callback" for row in values)
