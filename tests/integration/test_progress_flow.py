from __future__ import annotations


def test_progress_flow_returns_revised_plan_with_history(client):
    roadmap_response = client.post(
        "/roadmaps",
        json={
            "employee_profile": {
                "role": "Linux admin",
                "experience_level": "intermediate",
                "target_role": "DevOps engineer",
                "available_time_per_week": 6,
                "target_specializations": ["Terraform"],
            },
            "clarifying_questions_asked": 3,
        },
    )
    roadmap_payload = roadmap_response.json()
    roadmap = roadmap_payload["roadmap"]

    check_in_response = client.post(
        "/progress/check-ins",
        json={
            "employee_profile_id": roadmap["employee_profile_id"],
            "roadmap_id": roadmap["id"],
            "completed_steps": [roadmap["milestones"][0]["title"]],
            "new_goals": ["GitOps"],
            "notes": "Completed the immediate step",
        },
    )

    assert check_in_response.status_code == 200
    payload = check_in_response.json()
    assert payload["revision"]["prior_roadmap"]["id"] == roadmap["id"]
    assert payload["revision"]["updated_roadmap"]["previous_roadmap_id"] == roadmap["id"]
    assert payload["revision"]["updated_roadmap"]["id"] != roadmap["id"]

