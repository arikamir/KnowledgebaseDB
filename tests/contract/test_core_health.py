def test_liveness_is_process_local(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_only_failed_dependencies(app, client):
    app.state.readiness_checks = {
        "postgresql": lambda: True,
        "tenantJwks": lambda: False,
        "keyMaterial": lambda: True,
    }
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unready", "failedDependencies": ["tenantJwks"]}
    assert response.headers["x-correlation-id"]
