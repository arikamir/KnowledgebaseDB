"""Human-friendly formatting for roadmap outputs."""

from __future__ import annotations

from dataclasses import dataclass

from knowledge.schemas import CareerRoadmap, RoadmapStep, TimeHorizon, enum_text


TIME_HORIZON_ORDER = {
    TimeHorizon.IMMEDIATE.value: 0,
    TimeHorizon.NEAR_TERM.value: 1,
    TimeHorizon.LONG_TERM.value: 2,
}


@dataclass(slots=True)
class RoadmapPresentation:
    text: str
    follow_up_prompt: str


def sort_steps(steps: list[RoadmapStep]) -> list[RoadmapStep]:
    return sorted(
        steps,
        key=lambda step: (
            TIME_HORIZON_ORDER.get(enum_text(step.time_horizon), 99),
            step.priority,
            step.title.lower(),
        ),
    )


def format_roadmap(roadmap: CareerRoadmap) -> str:
    lines: list[str] = [
        f"Goal: {roadmap.goal_summary}",
        f"Current focus: {roadmap.current_focus}",
        f"Status: {roadmap.status}",
    ]

    if roadmap.assumptions:
        lines.append("Assumptions:")
        lines.extend(f"- {assumption}" for assumption in roadmap.assumptions)

    lines.append("Roadmap steps:")
    for step in sort_steps(roadmap.milestones):
        lines.extend(
            [
                f"- [{enum_text(step.time_horizon)}] {step.title}",
                f"  Skill area: {step.skill_area}",
                f"  Experience fit: {step.experience_level_fit}",
                f"  Next action: {step.concrete_next_action}",
                f"  Why it matters: {step.reason_it_matters}",
            ]
        )

    return "\n".join(lines)


def build_follow_up_prompt(roadmap: CareerRoadmap) -> str:
    ordered_steps = sort_steps(roadmap.next_actions or roadmap.milestones)
    if not ordered_steps:
        return "What part of your DevOps growth would you like to refine next?"

    first_step = ordered_steps[0]
    return (
        f"Which step would you like to start with: {first_step.skill_area} "
        f"or another part of the roadmap?"
    )


def present_roadmap(roadmap: CareerRoadmap) -> RoadmapPresentation:
    return RoadmapPresentation(
        text=format_roadmap(roadmap),
        follow_up_prompt=build_follow_up_prompt(roadmap),
    )
