from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select, update

from agent.contracts.roadmap import RoadmapIntakeRequest
from auth.bearer import ValidatedPrincipal
from knowledge.schemas import EmployeeProfile
from storage.operation_models import IdempotencyRecord
from storage.progress_models import ProgressCheckInRecord
from storage.roadmap_models import OwnedRoadmapRecord


def employee_principal(actor_id: str) -> ValidatedPrincipal:
    return ValidatedPrincipal(
        "employee",
        "tenant-progress",
        actor_id,
        "bff-progress",
        frozenset({"CareerAgent.Access"}),
        frozenset(),
    )


def application_principal(actor_id: str) -> ValidatedPrincipal:
    return ValidatedPrincipal(
        "application",
        "tenant-progress",
        actor_id,
        actor_id,
        frozenset(),
        frozenset({"CareerAgent.Progress.Write"}),
    )


def create_owned_roadmap(app_container, *, employee: str | None = None, application: str | None = None):
    result = app_container.roadmap_service.create_owned_roadmap(
        RoadmapIntakeRequest(employee_profile=EmployeeProfile(
            role="Linux administrator",
            experience_level="intermediate",
            target_role="DevOps engineer",
            available_time_per_week=6,
            target_specializations=["Terraform"],
        )),
        employee_identity_id=employee,
        machine_principal_id=application,
    )
    assert result.roadmap is not None
    owner = (
        {"employee_identity_id": employee}
        if employee is not None
        else {"machine_principal_id": application}
    )
    return app_container.progress_repository.get_owned_roadmap_context(
        result.roadmap.id,
        **owner,
    ).roadmap


def progress_headers(key: str = "progress-action-key-0001") -> dict[str, str]:
    return {"Authorization": "Bearer progress-token", "Idempotency-Key": key}


def record_count(app_container, model) -> int:
    with app_container.database.session() as session:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_employee_progress_normalizes_explicit_and_all_matching_legacy_references(client, app_container):
    roadmap = create_owned_roadmap(app_container, employee="employee-progress")
    with app_container.database.session() as session:
        stored = session.get(OwnedRoadmapRecord, roadmap.id)
        snapshot = dict(stored.profile_snapshot["roadmap"])
        milestones = [dict(item) for item in snapshot["milestones"]]
        milestones[1]["skill_area"] = milestones[0]["skill_area"]
        snapshot["milestones"] = milestones
        stored.profile_snapshot = {"roadmap": snapshot}
    roadmap = app_container.progress_repository.get_owned_roadmap_context(
        roadmap.id,
        employee_identity_id="employee-progress",
    ).roadmap
    client.app.state.validate_delegated_token = lambda _token: employee_principal("employee-progress")
    explicit = roadmap.milestones[2]
    legacy_matches = roadmap.milestones[:2]

    response = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers(),
        json={
            "roadmap_id": roadmap.id,
            "employee_profile_id": "ignored-authorization-hint",
            "notes": "  Preserve this note  ",
            "completed_milestone_keys": [explicit.milestone_key],
            "completed_steps": [legacy_matches[0].skill_area.upper(), "unknown legacy reference"],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["check_in"]["notes"] == "Preserve this note"
    assert payload["check_in"]["employee_profile_id"] == roadmap.employee_profile_id
    assert payload["check_in"]["completed_steps"] == [
        legacy_matches[0].skill_area.upper(),
        "unknown legacy reference",
    ]
    assert payload["check_in"]["normalized_milestone_keys"] == [
        explicit.milestone_key,
        legacy_matches[0].milestone_key,
        legacy_matches[1].milestone_key,
    ]
    assert len(payload["next_action"]) == 4
    assert payload["next_action"]["kind"] == "review_roadmap"


def test_unknown_explicit_key_is_rejected_and_schema_failure_does_not_claim_key(client, app_container):
    roadmap = create_owned_roadmap(app_container, employee="employee-strict")
    client.app.state.validate_delegated_token = lambda _token: employee_principal("employee-strict")

    schema_response = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers("progress-action-key-schema"),
        json={"roadmap_id": roadmap.id, "completed_milestone_keys": ["NOT-LOWERCASE"]},
    )
    unknown_response = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers("progress-action-key-unknown"),
        json={"roadmap_id": roadmap.id, "completed_milestone_keys": ["unknown-key"]},
    )

    assert schema_response.status_code == 422
    assert unknown_response.status_code == 422
    assert unknown_response.json()["code"] == "MILESTONE_KEY_UNKNOWN"
    assert record_count(app_container, ProgressCheckInRecord) == 0
    assert record_count(app_container, IdempotencyRecord) == 1


def test_cross_employee_reference_is_not_found_and_creates_no_check_in(client, app_container):
    roadmap = create_owned_roadmap(app_container, employee="employee-owner")
    client.app.state.validate_delegated_token = lambda _token: employee_principal("employee-foreign")

    response = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers(),
        json={"roadmap_id": roadmap.id, "notes": "Must not persist"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "ROADMAP_NOT_FOUND"
    assert record_count(app_container, ProgressCheckInRecord) == 0


def test_application_can_mutate_only_its_roadmap_and_cannot_restore_browser_review(client, app_container):
    roadmap = create_owned_roadmap(app_container, application="application-progress")
    foreign = create_owned_roadmap(app_container, application="application-foreign")
    client.app.state.validate_machine_token = lambda _token: application_principal("application-progress")

    denied = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers("progress-action-key-foreign"),
        json={"roadmap_id": foreign.id, "notes": "Must not cross owners"},
    )

    response = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers(),
        json={"roadmap_id": roadmap.id, "completed_steps": [roadmap.milestones[0].title]},
    )

    assert denied.status_code == 404
    assert response.status_code == 200, response.text
    assert response.json()["check_in"]["owner_type"] == "application"
    client.app.state.validate_delegated_token = lambda _token: application_principal("application-progress")
    restoration = client.get(
        f"/api/v1/progress/reviews?roadmap_id={roadmap.id}",
        headers={"Authorization": "Bearer progress-token"},
    )
    assert restoration.status_code == 401


def test_employee_latest_review_restores_and_same_key_replays_exact_result(client, app_container):
    roadmap = create_owned_roadmap(app_container, employee="employee-restore")
    client.app.state.validate_delegated_token = lambda _token: employee_principal("employee-restore")
    request = {"roadmap_id": roadmap.id, "notes": "Restore me"}

    created = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers(),
        json=request,
    )
    replayed = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers(),
        json=request,
    )
    restored = client.get(
        f"/api/v1/progress/reviews?roadmap_id={roadmap.id}",
        headers={"Authorization": "Bearer progress-token"},
    )

    assert created.status_code == replayed.status_code == restored.status_code == 200
    assert replayed.json() == created.json()
    assert restored.json() == created.json()
    assert record_count(app_container, ProgressCheckInRecord) == 1


def test_revision_conflict_retries_once_then_commits_one_check_in(client, app_container, monkeypatch):
    roadmap = create_owned_roadmap(app_container, employee="employee-retry")
    client.app.state.validate_delegated_token = lambda _token: employee_principal("employee-retry")
    original = app_container.progress_repository.commit_owned_review
    calls = 0

    def conflict_once(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            with app_container.database.session() as session:
                session.execute(
                    update(OwnedRoadmapRecord)
                    .where(OwnedRoadmapRecord.id == roadmap.id)
                    .values(updated_at=kwargs["expected_updated_at"] + timedelta(seconds=1))
                )
        return original(**kwargs)

    monkeypatch.setattr(app_container.progress_repository, "commit_owned_review", conflict_once)
    response = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers(),
        json={"roadmap_id": roadmap.id, "notes": "Retry once"},
    )

    assert response.status_code == 200, response.text
    assert calls == 2
    assert record_count(app_container, ProgressCheckInRecord) == 1


def test_second_revision_conflict_requires_reload_and_new_intended_action_key(
    client, app_container, monkeypatch
):
    roadmap = create_owned_roadmap(app_container, employee="employee-conflict")
    client.app.state.validate_delegated_token = lambda _token: employee_principal("employee-conflict")
    original = app_container.progress_repository.commit_owned_review
    calls = 0

    def always_conflict(**kwargs):
        nonlocal calls
        calls += 1
        with app_container.database.session() as session:
            session.execute(
                update(OwnedRoadmapRecord)
                .where(OwnedRoadmapRecord.id == roadmap.id)
                .values(updated_at=kwargs["expected_updated_at"] + timedelta(seconds=1))
            )
        return original(**kwargs)

    monkeypatch.setattr(app_container.progress_repository, "commit_owned_review", always_conflict)
    request = {"roadmap_id": roadmap.id, "notes": "These notes stay available"}
    first = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers("progress-conflict-key-0001"),
        json=request,
    )
    same_key = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers("progress-conflict-key-0001"),
        json=request,
    )

    assert first.status_code == same_key.status_code == 409
    assert first.json()["code"] == same_key.json()["code"] == "ROADMAP_VERSION_CONFLICT"
    assert "Reload" in first.json()["detail"]
    assert calls == 2
    assert request["notes"] == "These notes stay available"
    assert record_count(app_container, ProgressCheckInRecord) == 0

    authoritative = client.get(
        f"/api/v1/roadmaps/{roadmap.id}",
        headers={"Authorization": "Bearer progress-token"},
    )
    assert authoritative.status_code == 200
    monkeypatch.setattr(app_container.progress_repository, "commit_owned_review", original)
    new_key = client.post(
        "/api/v1/progress/check-ins",
        headers=progress_headers("progress-conflict-key-0002"),
        json=request,
    )
    assert new_key.status_code == 200, new_key.text
    assert new_key.json()["check_in"]["notes"] == request["notes"]


def test_next_action_falls_back_without_querying_learning_tables(client, app_container):
    roadmap = create_owned_roadmap(app_container, employee="employee-fallback")
    client.app.state.validate_delegated_token = lambda _token: employee_principal("employee-fallback")
    statements: list[str] = []

    from sqlalchemy import event

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement.casefold())

    event.listen(app_container.database.engine, "before_cursor_execute", capture)
    try:
        response = client.post(
            "/api/v1/progress/check-ins",
            headers=progress_headers(),
            json={"roadmap_id": roadmap.id},
        )
    finally:
        event.remove(app_container.database.engine, "before_cursor_execute", capture)

    assert response.status_code == 200, response.text
    assert response.json()["next_action"]["kind"] == "continue_milestone"
    assert not any("learning_" in statement or "review_attempt" in statement for statement in statements)
