import pytest

from agent.learning_timing import RequiredContentClock


def test_clock_starts_only_after_accessible_commit_and_stops_after_first_scored_explanation() -> None:
    clock = RequiredContentClock()
    assert clock.accumulated_ms == 0
    clock.start_after_accessible_commit(1_000)
    clock.finish_after_explanation_commit(61_000)
    assert clock.accumulated_ms == 60_000
    assert clock.segments[-1].reason == "first_scored_review_complete"
    clock.validate()


@pytest.mark.parametrize("reason", ["optional_material", "explicit_leave", "before_external_lab", "interruption", "retry_study"])
def test_declared_pause_reasons_exclude_time(reason: str) -> None:
    clock = RequiredContentClock()
    clock.start_after_accessible_commit(0)
    clock.pause(10_000, reason)
    clock.resume_on_visible_focus(40_000)
    clock.finish_after_explanation_commit(50_000)
    assert clock.accumulated_ms == 20_000
    assert [segment.reason for segment in clock.segments] == [reason, "first_scored_review_complete"]


def test_document_hidden_for_five_seconds_or_less_remains_counted() -> None:
    clock = RequiredContentClock()
    clock.start_after_accessible_commit(0)
    clock.document_hidden(10_000, 15_000)
    clock.finish_after_explanation_commit(20_000)
    assert clock.accumulated_ms == 20_000


def test_document_hidden_over_five_seconds_pauses_until_visible_focus() -> None:
    clock = RequiredContentClock()
    clock.start_after_accessible_commit(0)
    clock.document_hidden(10_000, 20_001)
    clock.finish_after_explanation_commit(30_001)
    assert clock.accumulated_ms == 20_000
    assert clock.segments[0].reason == "document_hidden"


def test_missing_negative_and_overlapping_evidence_are_failures() -> None:
    with pytest.raises(ValueError, match="MISSING"):
        RequiredContentClock().validate()
    negative = RequiredContentClock(); negative.start_after_accessible_commit(10)
    with pytest.raises(ValueError, match="NEGATIVE"):
        negative.pause(9, "invalid")
    overlapping = RequiredContentClock(); overlapping.start_after_accessible_commit(0); overlapping.pause(10, "one")
    overlapping.resume_on_visible_focus(5); overlapping.pause(15, "two")
    with pytest.raises(ValueError, match="OVERLAP"):
        overlapping.validate()
