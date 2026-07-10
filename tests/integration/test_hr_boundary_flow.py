from __future__ import annotations


def test_hr_boundary_request_is_rejected(client):
    response = client.post(
        "/roadmaps",
        json={
            "request_text": "Please help me prepare for my performance review and salary discussion.",
            "employee_profile": {},
            "clarifying_questions_asked": 0,
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["category"] == "hr"

