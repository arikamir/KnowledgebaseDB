from __future__ import annotations


def test_skill_guidance_flow_supports_aliases_and_fallbacks(client):
    supported = client.post(
        "/skills/guidance",
        json={
            "topic": "Opeshift",
            "employee_profile": {
                "role": "Platform engineer",
                "experience_level": "intermediate",
                "target_role": "DevOps engineer",
                "available_time_per_week": 5,
            },
        },
    )
    assert supported.status_code == 200
    supported_payload = supported.json()
    assert supported_payload["supported"] is True
    assert supported_payload["resolved_topic"] == "OpenShift"

    fallback = client.post(
        "/skills/guidance",
        json={
            "topic": "NotYetCoveredTopic",
            "employee_profile": {
                "role": "Platform engineer",
                "experience_level": "intermediate",
                "target_role": "DevOps engineer",
                "available_time_per_week": 5,
            },
        },
    )
    assert fallback.status_code == 200
    fallback_payload = fallback.json()
    assert fallback_payload["supported"] is False
    assert fallback_payload["suggestions"]

