from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "config/operational-alert-profile-v1.yaml"
TERRAFORM = ROOT / "infra/azure/monitoring.tf"


def profile() -> dict:
    return yaml.safe_load(PROFILE.read_text())


def test_profile_fixes_every_operational_threshold() -> None:
    p = profile()["evaluation"]
    assert p["readiness"] == {"thresholdReadyReplicas": 0, "consecutiveMinutes": 5}
    assert p["requestGate"] == {"minimumRequests": 20, "windowMinutes": 5, "consecutiveWindows": 2}
    assert p["errorRate"]["percent"] == 5
    assert p["latencyP95Seconds"] == {"ui-static": 2, "roadmap": 30, "guidance": 10, "personalized-other": 5}
    assert p["restartLoop"] == {"minimumRestarts": 3, "windowMinutes": 10}
    assert p["hpaSaturation"] == {"replicas": 4, "averageCpuPercent": 70, "warningMinutes": 15, "pageMinutes": 30}
    assert p["revocationOldestUnacknowledgedHours"] == {"warning": 2, "page": 6, "critical": 12}
    assert p["certificateExpiryDays"] == {"warning": [30, 14, 7], "criticalBelowHours": 48}
    assert p["directoryReconciliationHours"] == {"warning": 6, "page": 8}
    assert p["labValidationHours"] == {"warning": 30, "page": 36, "immediateFailureCount": 3, "unavailableImmediate": True}


def test_profile_routes_to_exact_operations_owners() -> None:
    routes = profile()["routing"]
    assert routes["readiness"] == ["application-operations"]
    assert routes["hpa-saturation"] == ["application-operations", "platform-operations"]
    assert routes["certificate-expiry"] == ["platform-operations"]
    assert routes["directory-reconciliation"] == ["application-operations", "platform-operations"]
    assert routes["lab-validation-warning"] == ["learning-content-operations"]
    assert routes["lab-validation-page"] == ["learning-content-operations", "application-operations"]


def test_terraform_materializes_profile_driven_rules_and_routes() -> None:
    source = TERRAFORM.read_text()
    assert "yamldecode(file" in source and "operational-alert-profile-v1.yaml" in source
    for signal in ("readiness", "request-error-rate", "latency-p95", "restart-loop", "hpa-warning", "hpa-page", "session-revocation", "certificate-expiry", "directory-reconciliation", "lab-validation"):
        assert signal in source
    for route in ("application-operations", "platform-operations", "learning-content-operations"):
        assert route in source
    assert "azurerm_monitor_scheduled_query_rules_alert_v2" in source
