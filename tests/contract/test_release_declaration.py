from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/contract/fixtures/gitops"


def run_validator(path: Path, **updates: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(updates)
    return subprocess.run(
        [str(ROOT / "scripts/ci/validate-release-bundle.sh"), str(path)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_schema_requires_provenance_and_exact_services() -> None:
    schema = json.loads((ROOT / "config/argocd-release.schema.json").read_text())
    assert {"sourceTag", "sourceRevision", "ciRun", "services", "validationEvidence"} <= set(schema["required"])
    assert set(schema["properties"]["services"]["required"]) == {"ui", "bff", "core"}
    assert schema["additionalProperties"] is False


def test_valid_bundle_accepts_protected_tag_and_matching_revision() -> None:
    result = run_validator(
        FIXTURES / "valid-release-bundle.json",
        REQUIRE_PROTECTED_TAG="true",
        GITHUB_REF_PROTECTED="true",
        GITHUB_SHA="0123456789abcdef0123456789abcdef01234567",
    )
    assert result.returncode == 0, result.stderr


def test_invalid_bundle_fixtures_fail_closed() -> None:
    for name in (
        "malformed-release-bundle.json",
        "tag-source-mismatch-release-bundle.json",
        "mutable-tag-release-bundle.json",
        "missing-service-release-bundle.json",
        "credential-containing-release-bundle.json",
    ):
        result = run_validator(FIXTURES / name)
        assert result.returncode != 0, name


def test_unprotected_bundle_requires_effective_protection() -> None:
    result = run_validator(FIXTURES / "unprotected-tag-release-bundle.json", REQUIRE_PROTECTED_TAG="true")
    assert result.returncode != 0


def test_release_version_uniqueness_rejects_reuse_for_other_revision(tmp_path: Path) -> None:
    ledger = tmp_path / "versions.tsv"
    ledger.write_text("1.2.3\tffffffffffffffffffffffffffffffffffffffff\n")
    result = subprocess.run(
        [str(ROOT / "scripts/ci/check-release-version-uniqueness.sh"), "1.2.3", "0123456789abcdef0123456789abcdef01234567"],
        cwd=ROOT,
        env={**os.environ, "RELEASE_VERSION_LEDGER": str(ledger)},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0


def test_writer_is_the_sole_declaration_shape_producer(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.json"
    declaration = tmp_path / "release.json"
    result = subprocess.run(
        [
            str(ROOT / "scripts/ci/write-gitops-release.sh"),
            "--manifest", str(FIXTURES / "release-manifest.json"),
            "--tag", "v9.9.9-rc.1+build.7",
            "--source-revision", "0123456789abcdef0123456789abcdef01234567",
            "--run-id", "github-999",
            "--output-bundle", str(bundle),
            "--output-declaration", str(declaration),
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "REQUIRE_PROTECTED_TAG": "true",
            "GITHUB_REF_PROTECTED": "true",
            "GITHUB_SHA": "0123456789abcdef0123456789abcdef01234567",
            "GITHUB_REPOSITORY": "arikamir/KnowledgebaseDB",
            "GITHUB_WORKFLOW": "delivery.yml",
        },
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(declaration.read_text())["sourceTag"] == "v9.9.9-rc.1+build.7"
