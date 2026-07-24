from __future__ import annotations

from pathlib import Path

from agent.contracts.roadmap import RoadmapIntakeRequest
from auth.bearer import BearerValidationError, ValidatedPrincipal


ROOT = Path(__file__).resolve().parents[2]


def machine(actor: str, *roles: str) -> ValidatedPrincipal:
    return ValidatedPrincipal("application", "tenant-machine", actor, actor, frozenset(), frozenset(roles))


def roadmap_payload() -> dict[str, object]:
    return {"employee_profile": {
        "role": "Linux administrator", "experience_level": "intermediate",
        "target_role": "DevOps engineer", "available_time_per_week": 6,
        "target_specializations": ["Terraform"],
    }}


def headers(key: str) -> dict[str, str]:
    return {"Authorization": "Bearer machine-token", "Idempotency-Key": key}


def test_machine_roadmap_guidance_and_progress_are_bff_ui_outage_independent(client) -> None:
    actor = "approved-machine-a"
    client.app.state.validate_delegated_token = lambda _token: (_ for _ in ()).throw(BearerValidationError("DELEGATED_TOKEN_INVALID"))
    client.app.state.validate_machine_token = lambda _token: machine(actor, "CareerAgent.Roadmap.Generate")
    created = client.post("/api/v1/roadmaps", headers=headers("machine-roadmap-0001"), json=roadmap_payload())
    assert created.status_code == 200, created.text
    roadmap = created.json()["roadmap"]

    client.app.state.validate_machine_token = lambda _token: machine(actor, "CareerAgent.Guidance.Read")
    guidance = client.post(
        "/api/v1/guidance", headers=headers("machine-guidance-0001"),
        json={"topic": "Terraform", "employee_profile": roadmap_payload()["employee_profile"]},
    )
    assert guidance.status_code == 200, guidance.text
    assert guidance.json()["supported"] is True

    client.app.state.validate_machine_token = lambda _token: machine(actor, "CareerAgent.Progress.Write")
    progress = client.post(
        "/api/v1/progress/check-ins", headers=headers("machine-progress-0001"),
        json={"roadmap_id": roadmap["id"], "completed_steps": [roadmap["milestones"][0]["title"]]},
    )
    assert progress.status_code == 200, progress.text
    assert progress.json()["check_in"]["owner_type"] == "application"


def test_cross_application_employee_and_impersonation_attempts_are_denied(client, app_container) -> None:
    owner = "approved-machine-owner"
    foreign = "approved-machine-foreign"
    owned = app_container.roadmap_service.create_owned_roadmap(
        RoadmapIntakeRequest.model_validate(roadmap_payload()),
        machine_principal_id=owner,
    ).roadmap
    assert owned is not None
    client.app.state.validate_machine_token = lambda _token: machine(foreign, "CareerAgent.Progress.Write")
    denied = client.post(
        "/api/v1/progress/check-ins", headers=headers("machine-cross-owner-0001"),
        json={"roadmap_id": owned.id, "notes": "must not cross owners"},
    )
    assert denied.status_code == 404
    assert denied.json()["code"] == "ROADMAP_NOT_FOUND"

    client.app.state.validate_machine_token = lambda _token: machine(foreign, "CareerAgent.Roadmap.Generate")
    employee_read = client.get(f"/api/v1/roadmaps/{owned.id}", headers={"Authorization": "Bearer machine-token"})
    assert employee_read.status_code == 401


def test_machine_operations_require_the_exact_app_role(client) -> None:
    client.app.state.validate_machine_token = lambda _token: machine("roleless-machine", "Wrong.Role")
    response = client.post("/api/v1/roadmaps", headers=headers("machine-role-denied-0001"), json=roadmap_payload())
    assert response.status_code == 403


def test_private_route_tls_source_and_network_controls_have_no_public_core_path() -> None:
    private = (ROOT / "deploy/k8s/overlays/aks-nonprod/private-machine-service.yaml").read_text()
    route = (ROOT / "deploy/k8s/overlays/aks-nonprod/httproute.yaml").read_text()
    core = (ROOT / "deploy/k8s/base/core/deployment.yaml").read_text()
    network = (ROOT / "deploy/k8s/base/network-policies.yaml").read_text()
    agc = (ROOT / "infra/azure/application-gateway-for-containers.tf").read_text()
    assert 'azure-load-balancer-internal: "true"' in private
    assert "PRIVATE_CORE_DNS_ZONE_NAME" in private and "PRIVATE_MACHINE_SOURCE_CIDR" in private
    assert "name: core" not in route and "core-private-machine" not in route
    assert "--ssl-certfile" in core and "scheme: HTTPS" in core
    assert "CORE_TLS_EXPECTED_SANS" in core and "CORE_TLS_EXPECTED_ISSUER" in core
    assert "core-private-callers" in network
    assert "browser_gateway_source_cidrs" in agc and "security_rule" in agc


def test_machine_registration_is_private_role_only_without_delegated_impersonation() -> None:
    registrations = (ROOT / "infra/azure/entra-machine-registrations.tf").read_text()
    core_api = (ROOT / "infra/azure/entra-core-api-registration.tf").read_text()
    for required in (
        "approved_machine_consumers", "app_role_assignment_required = true",
        "azuread_app_role_assignment", "app_role_ids[each.value.role]",
    ):
        assert required in registrations
    assert 'allowed_member_types = ["Application"]' in core_api
    for forbidden in ("delegated", "authorization_code", "redirect_uri", "impersonat"):
        assert forbidden not in registrations.lower()
