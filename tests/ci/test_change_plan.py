from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
DETECT = ROOT / "scripts/ci/detect-changes.sh"
DISPATCH = ROOT / "scripts/ci/validate-service.sh"
ALL_SERVICES = {"ui": True, "bff": True, "core": True}
NO_SERVICES = {"ui": False, "bff": False, "core": False}
ALL_LANES = {
    "contractIntegrity": True,
    "readinessScenarios": True,
    "performanceProfile": True,
    "infrastructure": True,
}
CONTRACT_ONLY = {
    "contractIntegrity": True,
    "readinessScenarios": False,
    "performanceProfile": False,
    "infrastructure": False,
}


def run(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=cwd, check=check, text=True, capture_output=True,
        env={**os.environ, "LC_ALL": "C"},
    )


def commit(repo: Path, path: str, content: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    run("git", "add", path, cwd=repo)
    run("git", "commit", "-m", path, cwd=repo)
    return run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str]:
    run("git", "init", "-q", cwd=tmp_path)
    run("git", "config", "user.email", "change-plan@example.invalid", cwd=tmp_path)
    run("git", "config", "user.name", "Change Plan Test", cwd=tmp_path)
    baseline = commit(tmp_path, "initial.txt", "initial")
    return tmp_path, baseline


def detect(repo: Path, source: str, baseline: str, *extra: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    output = repo / "change-plan.json"
    result = run(
        str(DETECT), "--source", source, "--baseline", baseline,
        "--output", str(output), *extra, cwd=repo, check=False,
    )
    return result, output


def plan_for(repository: tuple[Path, str], path: str) -> dict[str, object]:
    repo, baseline = repository
    source = commit(repo, path, "changed")
    result, output = detect(repo, source, baseline)
    assert result.returncode == 0, result.stderr
    return json.loads(output.read_text())


@pytest.mark.parametrize(
    ("path", "services"),
    [
        ("ui/src/app.tsx", {"ui": True, "bff": False, "core": False}),
        ("bff/src/app.ts", {"ui": False, "bff": True, "core": False}),
        ("src/api/main.py", {"ui": False, "bff": False, "core": True}),
    ],
)
def test_selects_independent_service_changes(
    repository: tuple[Path, str], path: str, services: dict[str, bool],
) -> None:
    plan = plan_for(repository, path)
    assert plan["services"] == services
    assert plan["validationLanes"] == CONTRACT_ONLY
    assert plan["reason"] == [path]


@pytest.mark.parametrize(
    ("path", "services"),
    [
        ("specs/003-develop-ui/contracts/bff-api-v1.openapi.yaml", {"ui": True, "bff": True, "core": False}),
        ("specs/003-develop-ui/contracts/core-api-v1.openapi.yaml", {"ui": False, "bff": True, "core": True}),
        ("specs/003-develop-ui/contracts/supported-guidance-topics-v1.yaml", ALL_SERVICES),
    ],
)
def test_selects_contract_producers_and_consumers(
    repository: tuple[Path, str], path: str, services: dict[str, bool],
) -> None:
    plan = plan_for(repository, path)
    assert plan["services"] == services
    assert plan["validationLanes"] == CONTRACT_ONLY


@pytest.mark.parametrize(
    ("path", "lanes"),
    [
        ("specs/003-develop-ui/contracts/implementation-readiness-contract.md", ALL_LANES),
        ("specs/003-develop-ui/requirements-traceability.md", {**CONTRACT_ONLY, "infrastructure": True}),
        ("tests/fixtures/readiness-scenario-manifest-v1.yaml", {**CONTRACT_ONLY, "readinessScenarios": True, "infrastructure": True}),
        ("tests/performance/performance-profile-v1.json", {**CONTRACT_ONLY, "performanceProfile": True}),
        ("tests/performance/interaction-performance-profile-v1.json", {**CONTRACT_ONLY, "performanceProfile": True}),
        ("tests/performance/interaction-performance-fixtures-v1.json", {**CONTRACT_ONLY, "performanceProfile": True}),
    ],
)
def test_normative_inputs_select_all_services_and_exact_lanes(
    repository: tuple[Path, str], path: str, lanes: dict[str, bool],
) -> None:
    plan = plan_for(repository, path)
    assert plan["services"] == ALL_SERVICES
    assert plan["validationLanes"] == lanes
    assert plan["services"] != NO_SERVICES


@pytest.mark.parametrize(
    "path",
    [
        ".agents/skills/provision-azure-app-resources/scripts/provision.sh",
        ".agents/skills/provision-azure-app-resources/assets/terraform/main.tf",
        ".agents/skills/teardown-azure-app-resources/scripts/teardown.sh",
        ".agents/skills/teardown-azure-app-resources/assets/terraform/main.tf",
    ],
)
def test_mandatory_skill_assets_select_all_services_and_infrastructure(
    repository: tuple[Path, str], path: str,
) -> None:
    plan = plan_for(repository, path)
    assert plan["services"] == ALL_SERVICES
    assert plan["validationLanes"] == {**CONTRACT_ONLY, "infrastructure": True}


def test_shared_build_selects_all_while_docs_publish_no_image(repository: tuple[Path, str]) -> None:
    shared = plan_for(repository, "compose.yaml")
    assert shared["services"] == ALL_SERVICES
    assert shared["validationLanes"] == CONTRACT_ONLY

    repo, _baseline = repository
    baseline = run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    source = commit(repo, "docs/operator-guide.md", "docs")
    result, output = detect(repo, source, baseline)
    assert result.returncode == 0
    docs = json.loads(output.read_text())
    assert docs["services"] == NO_SERVICES
    assert docs["validationLanes"] == CONTRACT_ONLY


def test_mixed_paths_boolean_or_without_clearing_and_sort_reasons(repository: tuple[Path, str]) -> None:
    repo, baseline = repository
    commit(repo, "ui/src/view.tsx", "ui")
    commit(repo, "tests/fixtures/readiness-scenario-manifest-v1.yaml", "manifest")
    source = commit(repo, "docs/readme.md", "docs")
    result, output = detect(repo, source, baseline)
    assert result.returncode == 0, result.stderr
    plan = json.loads(output.read_text())
    assert plan["services"] == ALL_SERVICES
    assert plan["validationLanes"] == {
        **CONTRACT_ONLY, "readinessScenarios": True, "infrastructure": True,
    }
    assert plan["reason"] == sorted(set(plan["reason"]))
    assert plan["reason"] == [
        "docs/readme.md", "tests/fixtures/readiness-scenario-manifest-v1.yaml", "ui/src/view.tsx",
    ]


def test_missing_baseline_is_json_null_and_selects_everything(repository: tuple[Path, str]) -> None:
    repo, _baseline = repository
    source = run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    output = repo / "change-plan.json"
    result = run(
        str(DETECT), "--source", source, "--missing-baseline", "--output", str(output),
        cwd=repo, check=False,
    )
    assert result.returncode == 0, result.stderr
    plan = json.loads(output.read_text())
    assert plan["baselineRevision"] is None
    assert plan["services"] == ALL_SERVICES
    assert plan["validationLanes"] == ALL_LANES
    assert plan["reason"] == ["missing-baseline"]


@pytest.mark.parametrize("baseline", ["HEAD", "deadbeef", "z" * 40])
def test_invalid_explicit_baseline_fails_closed(
    repository: tuple[Path, str], baseline: str,
) -> None:
    repo, _ = repository
    source = run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    result, output = detect(repo, source, baseline)
    assert result.returncode != 0
    assert not output.exists()


def test_resolvable_nonancestor_baseline_fails_closed(repository: tuple[Path, str]) -> None:
    repo, _ = repository
    source = run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    tree = run("git", "rev-parse", "HEAD^{tree}", cwd=repo).stdout.strip()
    unrelated = run("git", "commit-tree", tree, "-m", "unrelated", cwd=repo).stdout.strip()
    result, output = detect(repo, source, unrelated)
    assert result.returncode != 0
    assert not output.exists()


@pytest.mark.parametrize(
    ("mode", "reason"),
    [("--rebuild-all", "audited-rebuild-all"), ("--recovery", "audited-recovery")],
)
def test_audited_rebuild_and_recovery_require_distinct_approvers(
    repository: tuple[Path, str], mode: str, reason: str,
) -> None:
    repo, baseline = repository
    source = run("git", "rev-parse", "HEAD", cwd=repo).stdout.strip()
    denied, output = detect(
        repo, source, baseline, mode, "--recovery-operator", "operator-a",
        "--platform-approver", "operator-a",
    )
    assert denied.returncode != 0
    assert not output.exists()

    allowed, output = detect(
        repo, source, baseline, mode, "--recovery-operator", "operator-a",
        "--platform-approver", "approver-b",
    )
    assert allowed.returncode == 0, allowed.stderr
    plan = json.loads(output.read_text())
    assert plan["services"] == ALL_SERVICES
    assert plan["validationLanes"] == ALL_LANES
    assert plan["reason"] == [reason]


def test_dispatcher_consumes_plan_without_recalculating_paths(repository: tuple[Path, str]) -> None:
    repo, baseline = repository
    source = commit(repo, "ui/src/app.tsx", "ui")
    result, output = detect(repo, source, baseline)
    assert result.returncode == 0
    before = output.read_bytes()

    selected = run(
        str(DISPATCH), "--plan", str(output), "--service", "ui", "--", "sh", "-c", "printf selected",
        cwd=repo, check=False,
    )
    skipped = run(
        str(DISPATCH), "--plan", str(output), "--service", "core", "--", "sh", "-c", "exit 9",
        cwd=repo, check=False,
    )
    assert selected.returncode == 0 and selected.stdout == "selected"
    assert skipped.returncode == 0
    assert output.read_bytes() == before
