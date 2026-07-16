from agent.next_action import MilestoneCandidate, select_foundation_next_action


def test_roadmap_only_fallback_selects_lowest_incomplete_milestone() -> None:
    candidates = [
        MilestoneCandidate("roadmap-1", "z-stable", 1, "Second"),
        MilestoneCandidate("roadmap-1", "b-stable", 0, "First B"),
        MilestoneCandidate("roadmap-1", "a-stable", 0, "First A"),
    ]
    selected = select_foundation_next_action("roadmap-1", candidates)
    assert selected.action_type == "continue_milestone"
    assert selected.milestone_key == "a-stable"


def test_completed_roadmap_selects_review() -> None:
    selected = select_foundation_next_action("roadmap-1", [MilestoneCandidate("roadmap-1", "done", 0, "Done", True)])
    assert selected.action_type == "review_roadmap"
