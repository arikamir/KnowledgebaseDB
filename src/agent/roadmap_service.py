"""Roadmap synthesis and intake logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from agent.contracts.roadmap import ClarifyingQuestion, RoadmapIntakeRequest, RoadmapIntakeResponse
from agent.errors import BoundaryViolationError
from agent.policy import classify_request
from agent.roadmap_presenter import present_roadmap
from agent.settings import AppSettings
from knowledge.schemas import (
    CareerRoadmap,
    CompletionState,
    EmployeeProfile,
    ExperienceLevel,
    RoadmapStep,
    RoadmapStatus,
    TimeHorizon,
    enum_text,
)
from skills.catalog import SkillCatalog
from storage.roadmap_repository import RoadmapRepository


QUESTION_PRIORITY = [
    ("role", "What is your current role or strongest hands-on area?", "This anchors the roadmap to your starting point."),
    ("experience_level", "How would you describe your current experience level?", "This keeps the step difficulty realistic."),
    ("target_role", "What role or specialization are you aiming for?", "The target determines which skills should come first."),
    ("available_time_per_week", "How much time can you spend each week?", "The roadmap should fit the pace you can sustain."),
    ("learning_preferences", "Do you prefer hands-on projects, reading, or a mix?", "The plan should match how you learn best."),
    ("constraints", "Are there any constraints I should account for?", "Constraints shape the learning path and timing."),
]


TRACKS: dict[str, list[str]] = {
    "general": ["Linux", "Docker", "Kubernetes"],
    "delivery": ["Jenkins", "Docker", "Kubernetes"],
    "platform": ["Docker", "Kubernetes", "Argo CD"],
    "cloud": ["Terraform", "AWS", "Kubernetes"],
    "windows": ["Windows Administration", "MSI", "Azure DevOps"],
    "security": ["Certificates", "HashiCorp Vault", "SecOps"],
    "mlops": ["Docker", "Kubernetes", "MLOps"],
}


def _normalized_terms(profile: EmployeeProfile, request_text: str | None = None) -> str:
    parts = [profile.normalized_text()]
    if request_text:
        parts.append(request_text.lower())
    return " ".join(part for part in parts if part)


def _matches(term: str, haystack: str) -> bool:
    return term.lower() in haystack


@dataclass(slots=True)
class RoadmapService:
    repository: RoadmapRepository
    catalog: SkillCatalog
    settings: AppSettings

    def create_roadmap(self, request: RoadmapIntakeRequest) -> RoadmapIntakeResponse:
        self._ensure_boundary(request)
        profile = request.employee_profile
        missing_fields = profile.missing_core_fields()

        if missing_fields and request.clarifying_questions_asked < self.settings.max_clarifying_questions:
            questions = self._build_questions(
                missing_fields,
                remaining_slots=self.settings.max_clarifying_questions - request.clarifying_questions_asked,
            )
            return RoadmapIntakeResponse(
                status="needs_more_info",
                employee_profile_id=profile.id,
                clarifying_questions=questions,
            )

        roadmap, assumptions = self.build_roadmap(
            profile=profile,
            clarifying_questions_asked=request.clarifying_questions_asked,
            assumptions=self._build_assumptions(profile, missing_fields),
            request_text=request.request_text,
        )
        saved_profile = self.repository.save_employee_profile(profile)
        roadmap = roadmap.model_copy(update={"employee_profile_id": saved_profile.id})
        saved_roadmap = self.repository.save_roadmap(roadmap)
        presentation = present_roadmap(saved_roadmap)
        return RoadmapIntakeResponse(
            status="ready",
            employee_profile_id=saved_profile.id,
            roadmap_id=saved_roadmap.id,
            roadmap=saved_roadmap,
            assumptions=assumptions,
            presentation=presentation.text,
            follow_up_prompt=presentation.follow_up_prompt,
        )

    def build_roadmap(
        self,
        profile: EmployeeProfile,
        clarifying_questions_asked: int = 0,
        assumptions: list[str] | None = None,
        request_text: str | None = None,
    ) -> tuple[CareerRoadmap, list[str]]:
        assumptions = list(assumptions or [])
        track = self._choose_track(profile, request_text=request_text)
        sequence = self._build_topic_sequence(profile, track, request_text=request_text)
        if len(sequence) < 3:
            sequence = self._fill_topics(sequence, track)
        sequence = sequence[:3]

        immediate, near_term, long_term = sequence
        steps = [
            self._step_for_topic(immediate, TimeHorizon.IMMEDIATE, profile, priority=1),
            self._step_for_topic(near_term, TimeHorizon.NEAR_TERM, profile, priority=2),
            self._step_for_topic(long_term, TimeHorizon.LONG_TERM, profile, priority=3),
        ]

        roadmap = CareerRoadmap(
            employee_profile_id=profile.id,
            goal_summary=self._goal_summary(profile),
            current_focus=steps[0].title,
            milestones=steps,
            next_actions=steps[:2],
            status=RoadmapStatus.ACTIVE,
            assumptions=assumptions,
            clarifying_questions_asked=clarifying_questions_asked,
        )
        return roadmap, assumptions

    def suggest_steps_for_goals(
        self,
        profile: EmployeeProfile,
        goals: list[str],
        starting_priority: int = 10,
    ) -> list[RoadmapStep]:
        steps: list[RoadmapStep] = []
        priority = starting_priority
        for goal in goals:
            topic_name = self._choose_topic_for_text(goal, profile=profile)
            step = self._step_for_topic(
                topic_name,
                TimeHorizon.NEAR_TERM,
                profile,
                priority=priority,
                step_title=f"Advance {topic_name} toward {goal}",
                next_action_override=f"Turn the goal '{goal}' into one measurable practice task.",
                reason_override=f"Directly supports the new goal: {goal}.",
            )
            steps.append(step)
            priority += 1
        return steps

    def _ensure_boundary(self, request: RoadmapIntakeRequest) -> None:
        boundary_inputs = [request.request_text or "", request.employee_profile.normalized_text()]
        decision = classify_request(" ".join(boundary_inputs))
        if not decision.allowed:
            raise BoundaryViolationError(decision.reason, category=decision.category or "boundary")

    def _build_questions(self, missing_fields: list[str], remaining_slots: int) -> list[ClarifyingQuestion]:
        questions: list[ClarifyingQuestion] = []
        for field_name, prompt, why in QUESTION_PRIORITY:
            if field_name not in missing_fields:
                continue
            questions.append(ClarifyingQuestion(prompt=prompt, why_it_matters=why))
            if len(questions) >= remaining_slots:
                break
        return questions

    def _build_assumptions(self, profile: EmployeeProfile, missing_fields: list[str]) -> list[str]:
        assumptions: list[str] = []
        if "role" in missing_fields:
            assumptions.append("Assumed a general DevOps starting point because the current role was not provided.")
        if "experience_level" in missing_fields:
            assumptions.append("Assumed an early-career to mixed-experience baseline.")
        if "target_role" in missing_fields:
            assumptions.append("Assumed DevOps or platform engineering as the target direction.")
        if "available_time_per_week" in missing_fields:
            assumptions.append("Assumed roughly 4 hours per week for career-growth work.")
        if "learning_preferences" in missing_fields:
            assumptions.append("Assumed a hands-on learning preference.")
        if "constraints" in missing_fields:
            assumptions.append("Assumed no unusual scheduling or domain constraints.")
        if profile.target_specializations:
            assumptions.append(
                f"Used the stated specializations to bias the roadmap toward {', '.join(profile.target_specializations)}."
            )
        return assumptions

    def _goal_summary(self, profile: EmployeeProfile) -> str:
        current = profile.role or "your current role"
        target = profile.target_role or "a stronger DevOps role"
        return f"Move from {current} toward {target}"

    def _choose_track(self, profile: EmployeeProfile, request_text: str | None = None) -> str:
        haystack = _normalized_terms(profile, request_text)
        if any(_matches(term, haystack) for term in ["windows", "msi", "advanced installer", "packaging"]):
            return "windows"
        if any(_matches(term, haystack) for term in ["security", "secops", "vault", "certificate"]):
            return "security"
        if "mlops" in haystack:
            return "mlops"
        if any(_matches(term, haystack) for term in ["aws", "cloud", "terraform", "vmware"]):
            return "cloud"
        if any(_matches(term, haystack) for term in ["kubernetes", "argocd", "helm", "docker", "openshift"]):
            return "platform"
        if any(_matches(term, haystack) for term in ["jenkins", "azure devops", "gitlab ci", "cicd"]):
            return "delivery"
        return "general"

    def _choose_topic_for_text(self, text: str, profile: EmployeeProfile | None = None) -> str:
        haystack = text.lower()
        if profile:
            haystack += " " + profile.normalized_text()
        for topic in self.catalog.active_topics():
            names = [topic.name, *topic.aliases]
            if any(term.lower() in haystack for term in names):
                return topic.name
        return self._fill_topics([], self._choose_track(profile or EmployeeProfile()), limit=1)[0]

    def _build_topic_sequence(
        self,
        profile: EmployeeProfile,
        track: str,
        request_text: str | None = None,
    ) -> list[str]:
        haystack = _normalized_terms(profile, request_text)
        matches: list[str] = []
        for topic in self.catalog.active_topics():
            names = [topic.name, *topic.aliases]
            if any(term.lower() in haystack for term in names):
                matches.append(topic.name)
        return self._fill_topics(matches, track)

    def _fill_topics(self, topics: list[str], track: str, limit: int = 3) -> list[str]:
        ordered = list(topics)
        for candidate in TRACKS.get(track, TRACKS["general"]):
            topic = self.catalog.get_active(candidate)
            if topic and topic.name not in ordered:
                ordered.append(topic.name)
            if len(ordered) >= limit:
                return ordered[:limit]

        for candidate in TRACKS["general"]:
            topic = self.catalog.get_active(candidate)
            if topic and topic.name not in ordered:
                ordered.append(topic.name)
            if len(ordered) >= limit:
                return ordered[:limit]

        for topic in self.catalog.active_topics():
            if topic.name not in ordered:
                ordered.append(topic.name)
            if len(ordered) >= limit:
                break
        return ordered[:limit]

    def _step_for_topic(
        self,
        topic_name: str,
        horizon: TimeHorizon,
        profile: EmployeeProfile,
        priority: int,
        step_title: str | None = None,
        next_action_override: str | None = None,
        reason_override: str | None = None,
    ) -> RoadmapStep:
        topic = self.catalog.get_active(topic_name) or self.catalog.get(topic_name)
        if topic is None:
            raise ValueError(f"Unknown topic: {topic_name}")

        level_text = enum_text(profile.experience_level).lower() if profile.experience_level else "unknown"
        fit = topic.current_level_fit or f"Fit for {level_text} experience."
        experience_level = level_text
        if experience_level == ExperienceLevel.BEGINNER.value:
            fit = f"{fit} Good for a beginner learning path."
        elif experience_level == ExperienceLevel.INTERMEDIATE.value:
            fit = f"{fit} Good for an intermediate growth path."
        elif experience_level == ExperienceLevel.ADVANCED.value:
            fit = f"{fit} Good for an advanced stretch path."

        title = step_title or f"Build capability in {topic.name}"
        next_action = next_action_override or topic.practical_next_action
        reason = reason_override or topic.description
        if profile.target_role:
            reason = f"{reason} This supports progress toward {profile.target_role}."

        return RoadmapStep(
            title=title,
            skill_area=topic.name,
            experience_level_fit=fit,
            time_horizon=horizon,
            concrete_next_action=next_action,
            reason_it_matters=reason,
            priority=priority,
            completion_state=CompletionState.PENDING,
            supporting_notes=list(topic.related_skills),
        )
