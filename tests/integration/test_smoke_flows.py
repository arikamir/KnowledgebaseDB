from __future__ import annotations


def test_root_redirects_to_browser_documentation(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
    assert client.get(response.headers["location"]).status_code == 200


def test_smoke_endpoints_respond(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    roadmap = client.post(
        "/roadmaps",
        json={
            "employee_profile": {
                "role": "Windows administrator",
                "experience_level": "beginner",
                "target_role": "DevOps engineer",
                "available_time_per_week": 5,
            },
            "clarifying_questions_asked": 3,
        },
    )
    assert roadmap.status_code == 200

    skills = client.post(
        "/skills/guidance",
        json={
            "topic": "Terraform",
            "employee_profile": {
                "role": "Infrastructure engineer",
                "experience_level": "intermediate",
                "target_role": "Platform engineer",
                "available_time_per_week": 5,
            },
        },
    )
    assert skills.status_code == 200
