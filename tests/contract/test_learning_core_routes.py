from auth.bearer import ValidatedPrincipal
from fastapi.testclient import TestClient


def test_owner_scoped_learning_routes_and_exact_replay(app, app_container) -> None:
    app.state.validate_delegated_token = lambda _token: ValidatedPrincipal("employee", "tenant", "employee-route", "bff", frozenset({"CareerAgent.Access"}), frozenset())
    repository = app_container.learning_repository
    repository.publish_fixture(
        content_id="route-content", content_version="v1", roadmap_id="roadmap-route", milestone_key="m1",
        title="Route learning", objective="Complete safely", estimated_minutes=20,
        steps=[("route-read", "reading", "Read"), ("route-review", "review", "Review")],
        questions=[(f"route-q{i}", f"Q{i}", {"a": "A", "b": "B"}, "a", "Because") for i in range(3)],
    )
    client = TestClient(app)
    auth = {"Authorization": "Bearer token"}
    start_headers = {**auth, "Idempotency-Key": "route-start-key-01"}
    started = client.post("/api/v1/learning-sessions/route-content/start", headers=start_headers)
    replay = client.post("/api/v1/learning-sessions/route-content/start", headers=start_headers)
    assert started.status_code == replay.status_code == 200
    assert started.json()["id"] == replay.json()["id"]
    session_id = started.json()["id"]
    attempt = client.post(f"/api/v1/learning-sessions/{session_id}/review-attempts", headers={**auth, "Idempotency-Key": "route-attempt-key1"})
    assert attempt.status_code == 200
    attempt_id = attempt.json()["id"]
    for index in range(3):
        response = client.put(f"/api/v1/review-attempts/{attempt_id}/answers/route-q{index}", headers={**auth, "Idempotency-Key": f"route-answer-key{index}"}, json={"answer_key": "a"})
        assert response.status_code == 200
        assert set(response.json()) == {"question_id", "submitted_answer_key", "correct", "explanation", "answered_at"}
    submitted = client.post(f"/api/v1/review-attempts/{attempt_id}/submit", headers={**auth, "Idempotency-Key": "route-submit-key1"})
    assert submitted.status_code == 200
    assert submitted.json()["passed"] is True


def test_foreign_learning_resource_is_not_disclosed(app, app_container) -> None:
    app.state.validate_delegated_token = lambda _token: ValidatedPrincipal("employee", "tenant", "owner", "bff", frozenset({"CareerAgent.Access"}), frozenset())
    repository = app_container.learning_repository
    repository.publish_fixture(content_id="private-content", content_version="v1", roadmap_id="roadmap", milestone_key="m", title="Private", objective="Private", estimated_minutes=20, steps=[("p-read", "reading", "Read"), ("p-review", "review", "Review")], questions=[(f"p-q{i}", "Q", {"a": "A", "b": "B"}, "a", "Why") for i in range(3)])
    session = app_container.learning_service.start("other-owner", "private-content", "v1")
    response = TestClient(app).get(f"/api/v1/learning-sessions/{session['id']}", headers={"Authorization": "Bearer token"})
    assert response.status_code == 404
    assert response.json()["code"] == "LEARNING_SESSION_NOT_FOUND"
