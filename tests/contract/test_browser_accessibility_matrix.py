from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = json.loads((ROOT / "config/browser-accessibility-matrix-v1.json").read_text())


def test_browser_versions_platforms_viewports_and_assistive_technology_are_frozen() -> None:
    assert MATRIX["schemaVersion"] == 1 and MATRIX["status"] == "approved-for-execution"
    assert MATRIX["frozenAt"] == "2026-07-17T00:00:00Z"
    assert {name: value["majors"] for name, value in MATRIX["browsers"].items()} == {
        "chrome": [150, 149], "edge": [150, 149], "firefox": [152, 151], "safari": [26, 18],
    }
    assert all(len(value["exactDesktopVersions"]) == 2 and value["source"].startswith("https://") for value in MATRIX["browsers"].values())
    assert MATRIX["desktop"]["windows"]["widths"] == [320, 375, 768, 1024, 1440, 1920]
    assert MATRIX["desktop"]["macos"]["widths"] == [320, 375, 768, 1024, 1440, 1920]
    assert "NVDA latest with Chrome 150" in MATRIX["desktop"]["windows"]["assistiveTechnology"]
    assert "VoiceOver with Safari 26.5" in MATRIX["desktop"]["macos"]["assistiveTechnology"]
    assert MATRIX["mobile"]["viewports"] == [
        {"width": 375, "height": 812}, {"width": 812, "height": 375}, {"width": 320, "height": 568},
    ]
    assert MATRIX["magnification"]["zoom200Percent"] == ["chrome", "edge", "firefox", "safari"]
    assert MATRIX["magnification"]["textScaling200Percent"] == ["chrome", "safari"]


def test_all_journeys_states_and_fail_closed_evidence_policy_are_exact() -> None:
    assert MATRIX["journeys"] == ["roadmap", "guidance", "focused-learning", "progress-review"]
    assert MATRIX["persistenceStates"] == ["not_yet_saved", "saving", "save_unknown", "failed_to_save", "saved"]
    assert MATRIX["resultPolicy"] == {
        "requiredOutcome": "passed",
        "setupDependencyCrashTimeoutOrMissingEvidence": "failed",
        "substitution": "prohibited",
        "denominatorReduction": "prohibited",
    }


def test_required_automation_and_manual_evidence_artifacts_are_present() -> None:
    assert (ROOT / "ui/tests/e2e/accessibility.spec.ts").is_file()
    assert (ROOT / "ui/tests/e2e/persistence-status.spec.ts").is_file()
    assert (ROOT / "ui/tests/e2e/navigation-session.spec.ts").is_file()
    assert (ROOT / "specs/003-develop-ui/browser-accessibility-results.md").is_file()
