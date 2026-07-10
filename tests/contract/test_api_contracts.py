from __future__ import annotations


def test_openapi_exposes_feature_routes(client):
    schema = client.get("/openapi.json").json()

    paths = schema["paths"]
    assert "/roadmaps" in paths
    assert "/skills/guidance" in paths
    assert "/progress/check-ins" in paths

