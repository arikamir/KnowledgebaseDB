"""Monotonic accumulated required-content timing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClockSegment:
    started_ms: float
    ended_ms: float
    reason: str

    @property
    def duration_ms(self) -> float:
        return self.ended_ms - self.started_ms


class RequiredContentClock:
    def __init__(self) -> None:
        self._active_since: float | None = None
        self._segments: list[ClockSegment] = []

    def start_after_accessible_commit(self, now_ms: float) -> None:
        if self._active_since is None:
            self._active_since = now_ms

    def pause(self, now_ms: float, reason: str) -> None:
        if self._active_since is None:
            return
        if now_ms < self._active_since:
            raise ValueError("REQUIRED_CLOCK_NEGATIVE_SEGMENT")
        self._segments.append(ClockSegment(self._active_since, now_ms, reason))
        self._active_since = None

    def resume_on_visible_focus(self, now_ms: float) -> None:
        if self._active_since is None:
            self._active_since = now_ms

    def document_hidden(self, hidden_at_ms: float, visible_at_ms: float) -> None:
        if visible_at_ms < hidden_at_ms:
            raise ValueError("REQUIRED_CLOCK_NEGATIVE_SEGMENT")
        if visible_at_ms - hidden_at_ms > 5_000:
            self.pause(hidden_at_ms, "document_hidden")
            self.resume_on_visible_focus(visible_at_ms)

    def finish_after_explanation_commit(self, now_ms: float) -> None:
        self.pause(now_ms, "first_scored_review_complete")

    @property
    def segments(self) -> tuple[ClockSegment, ...]:
        return tuple(self._segments)

    @property
    def accumulated_ms(self) -> float:
        return sum(segment.duration_ms for segment in self._segments)

    def validate(self) -> None:
        previous_end: float | None = None
        for segment in self._segments:
            if segment.duration_ms < 0:
                raise ValueError("REQUIRED_CLOCK_NEGATIVE_SEGMENT")
            if previous_end is not None and segment.started_ms < previous_end:
                raise ValueError("REQUIRED_CLOCK_OVERLAP")
            previous_end = segment.ended_ms
        if not self._segments:
            raise ValueError("REQUIRED_CLOCK_MISSING")
