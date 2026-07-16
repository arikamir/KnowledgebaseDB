from __future__ import annotations

from pathlib import Path

import pytest

from agent.contracts.skill_guidance import TopicGuidanceRequest
from agent.skill_guidance_service import SkillGuidanceService
from api.errors import ApiProblem
from skills.catalog import SkillCatalog


ROOT = Path(__file__).resolve().parents[2]


def request(topic: str) -> TopicGuidanceRequest:
    return TopicGuidanceRequest(
        topic=topic,
        employee_profile={
            "role": "Platform engineer",
            "experience_level": "intermediate",
            "target_role": "DevOps engineer",
            "available_time_per_week": 5,
        },
    )


def catalog() -> SkillCatalog:
    return SkillCatalog.load(ROOT / "config/supported-guidance-topics-v1.yaml")


@pytest.mark.parametrize("value", ["kubernetes", "KUBERNETES", " k8s ", "Kubernetes cluster"])
def test_active_id_name_or_alias_resolves_without_silent_substitution(value: str) -> None:
    service = SkillGuidanceService(catalog())
    topic = service.resolve_active_topic(value)
    result = service.generate_active_guidance(request(value), topic)
    assert result.requested_topic == value
    assert result.resolved_topic == "Kubernetes"
    assert result.supported is True


@pytest.mark.parametrize(
    ("state", "retryable"),
    [("unavailable", True), ("retired", False)],
)
def test_known_nonactive_topic_has_stable_pre_key_outcome(state: str, retryable: bool) -> None:
    current = catalog()
    current._states["kubernetes"] = state
    current._states["k8s"] = state
    service = SkillGuidanceService(current)
    with pytest.raises(ApiProblem) as raised:
        service.resolve_active_topic("k8s")
    assert raised.value.code == "GUIDANCE_TOPIC_UNAVAILABLE"
    assert raised.value.retryable is retryable
    assert raised.value.field_errors == {"topic": [raised.value.detail]}


@pytest.mark.parametrize("value", ["unknown thing", "totally unrelated"])
def test_no_match_is_field_associated_and_pre_key(value: str) -> None:
    with pytest.raises(ApiProblem) as raised:
        SkillGuidanceService(catalog()).resolve_active_topic(value)
    assert raised.value.code == "GUIDANCE_TOPIC_UNINTERPRETABLE"
    assert "topic" in (raised.value.field_errors or {})


def test_ambiguous_exact_alias_is_not_silently_substituted() -> None:
    first = catalog().topics[0].model_copy(update={"aliases": ["shared"]})
    second = catalog().topics[1].model_copy(update={"aliases": ["shared"]})
    ambiguous = SkillCatalog([first, second])
    with pytest.raises(ApiProblem) as raised:
        SkillGuidanceService(ambiguous).resolve_active_topic("shared")
    assert raised.value.code == "GUIDANCE_TOPIC_UNINTERPRETABLE"


def test_schema_invalid_request_uses_stable_validation_problem(app) -> None:
    from auth.bearer import ValidatedPrincipal
    from fastapi.testclient import TestClient

    app.state.validate_delegated_token = lambda _token: ValidatedPrincipal(
        "employee", "tenant", "employee-a", "bff", frozenset({"CareerAgent.Access"}), frozenset()
    )
    response = TestClient(app).post(
        "/api/v1/guidance",
        headers={"Authorization": "Bearer token", "Idempotency-Key": "guidance-key-0001"},
        json={"topic": 42, "employee_profile": {}},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_FAILED"


def test_active_route_claims_key_and_replays_canonical_result(app, app_container) -> None:
    from auth.bearer import ValidatedPrincipal
    from fastapi.testclient import TestClient

    app.state.validate_delegated_token = lambda _token: ValidatedPrincipal(
        "employee", "tenant", "employee-a", "bff", frozenset({"CareerAgent.Access"}), frozenset()
    )
    client = TestClient(app)
    headers = {
        "Authorization": "Bearer token", "Idempotency-Key": "guidance-key-0002",
        "X-Guidance-Catalog-Version": app_container.catalog.catalog_version,
    }
    payload = {"topic": " K8S ", "employee_profile": {"role": "Administrator", "experience_level": "beginner"}}
    first = client.post("/api/v1/guidance", headers=headers, json=payload)
    replay = client.post("/api/v1/guidance", headers=headers, json=payload)
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert first.json()["requested_topic"] == " K8S "
    assert first.json()["resolved_topic"] == "Kubernetes"


def test_catalog_version_mismatch_is_compatibility_failure_before_key(app, app_container) -> None:
    from auth.bearer import ValidatedPrincipal
    from fastapi.testclient import TestClient
    from storage.operation_models import IdempotencyRecord

    app.state.validate_delegated_token = lambda _token: ValidatedPrincipal(
        "employee", "tenant", "employee-b", "bff", frozenset({"CareerAgent.Access"}), frozenset()
    )
    response = TestClient(app).post(
        "/api/v1/guidance",
        headers={
            "Authorization": "Bearer token", "Idempotency-Key": "guidance-key-0003",
            "X-Guidance-Catalog-Version": "99.0.0",
        },
        json={"topic": "Kubernetes", "employee_profile": {}},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CONTRACT_VERSION_UNSUPPORTED"
    with app_container.database.session() as session:
        assert session.query(IdempotencyRecord).count() == 0


@pytest.mark.parametrize("value", ["", " ", "x" * 129])
def test_invalid_topic_has_stable_validation_problem(value: str) -> None:
    with pytest.raises(ApiProblem) as raised:
        SkillGuidanceService(catalog()).resolve_active_topic(value)
    assert raised.value.code == "VALIDATION_FAILED"
    assert raised.value.retryable is False


def test_catalog_outage_is_not_reclassified_as_a_topic_error() -> None:
    class UnavailableCatalog:
        def exact_matches(self, _value: str):
            raise OSError("catalog storage unavailable")

    service = SkillGuidanceService(UnavailableCatalog())  # type: ignore[arg-type]
    with pytest.raises(ApiProblem) as raised:
        service.resolve_active_topic("Kubernetes")
    assert raised.value.code == "CAPABILITY_METADATA_UNAVAILABLE"
    assert raised.value.status == 503
    assert raised.value.retryable is True


def test_rejection_does_not_claim_an_idempotency_key(app_container) -> None:
    service = app_container.skill_guidance_service
    with pytest.raises(ApiProblem):
        service.resolve_active_topic("not present")
    with app_container.database.session() as session:
        from storage.operation_models import IdempotencyRecord

        assert session.query(IdempotencyRecord).count() == 0
