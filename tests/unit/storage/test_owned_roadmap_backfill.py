from storage.roadmap_models import classify_legacy_roadmap, stable_milestone_key


def test_verified_legacy_roadmap_enriches_with_stable_ordered_keys() -> None:
    payload = {"milestones": [{"title": "Container fundamentals"}, {"title": "Delivery automation", "completion_state": "completed"}]}
    state, milestones = classify_legacy_roadmap(payload, owner_verified=True)
    assert state == "enriched"
    assert [item["ordinal"] for item in milestones] == [0, 1]
    assert milestones[0]["milestone_key"] == stable_milestone_key("Container fundamentals", 0)
    assert len({item["milestone_key"] for item in milestones}) == 2


def test_unverified_owner_or_malformed_milestone_stays_legacy_only() -> None:
    assert classify_legacy_roadmap({"milestones": [{"title": "Valid"}]}, False) == ("legacy_only", [])
    assert classify_legacy_roadmap({"milestones": [{"title": ""}]}, True) == ("legacy_only", [])
