from __future__ import annotations


def test_roadmap_flow_asks_questions_then_returns_roadmap(client):
    sparse = {
        "employee_profile": {
            "role": "",
            "experience_level": None,
            "target_role": None,
            "available_time_per_week": None,
        },
        "clarifying_questions_asked": 0,
    }

    first = client.post("/roadmaps", json=sparse)
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["status"] == "needs_more_info"
    assert 1 <= len(first_payload["clarifying_questions"]) <= 3

    complete = {
        "employee_profile": {
            "role": "Windows administrator",
            "experience_level": "beginner",
            "target_role": "DevOps engineer",
            "available_time_per_week": 5,
            "target_specializations": ["Kubernetes", "Azure DevOps"],
        },
        "clarifying_questions_asked": 3,
    }

    second = client.post("/roadmaps", json=complete)
    assert second.status_code == 200
    payload = second.json()
    assert payload["status"] == "ready"
    assert payload["roadmap_id"]
    assert payload["presentation"]
    assert payload["follow_up_prompt"]

