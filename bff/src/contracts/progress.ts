export interface BrowserProgressCheckInRequest {
  employeeProfileId?: string | null;
  roadmapId: string;
  notes?: string;
  completedSteps?: string[];
  completedMilestoneKeys?: string[];
  newGoals?: string[];
}

type JsonObject = Record<string, unknown>;

function object(value: unknown): JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as JsonObject
    : {};
}

function array(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function strings(value: unknown): string[] {
  return array(value).map(String);
}

export function toCoreProgressCheckIn(request: BrowserProgressCheckInRequest): JsonObject {
  return {
    employee_profile_id: request.employeeProfileId,
    roadmap_id: request.roadmapId,
    notes: request.notes ?? "",
    completed_steps: request.completedSteps ?? [],
    completed_milestone_keys: request.completedMilestoneKeys ?? [],
    new_goals: request.newGoals ?? [],
  };
}

export function toBrowserRoadmapMilestone(value: JsonObject): JsonObject {
  return {
    id: value.id,
    milestoneKey: value.milestone_key,
    ordinal: value.ordinal,
    title: value.title,
    skillArea: value.skill_area,
    experienceLevelFit: value.experience_level_fit,
    timeHorizon: value.time_horizon,
    concreteNextAction: value.concrete_next_action,
    reasonItMatters: value.reason_it_matters,
    priority: value.priority,
    completionState: value.completion_state,
    supportingNotes: strings(value.supporting_notes),
  };
}

function toBrowserRoadmap(value: JsonObject): JsonObject {
  return {
    id: value.id,
    employeeProfileId: value.employee_profile_id,
    previousRoadmapId: value.previous_roadmap_id ?? null,
    goalSummary: value.goal_summary,
    currentFocus: value.current_focus,
    milestones: array(value.milestones).map((item) => toBrowserRoadmapMilestone(object(item))),
    status: value.status,
    assumptions: strings(value.assumptions),
    clarifyingQuestionsAsked: value.clarifying_questions_asked,
    createdAt: value.created_at,
    updatedAt: value.updated_at,
  };
}

function toBrowserRevision(value: JsonObject): JsonObject {
  return {
    priorRoadmap: toBrowserRoadmap(object(value.prior_roadmap)),
    updatedRoadmap: toBrowserRoadmap(object(value.updated_roadmap)),
    completedSteps: strings(value.completed_steps),
    normalizedMilestoneKeys: strings(value.normalized_milestone_keys),
    newGoals: strings(value.new_goals),
    summary: value.summary,
    createdAt: value.created_at,
  };
}

function toBrowserCheckIn(value: JsonObject): JsonObject {
  return {
    id: value.id,
    employeeProfileId: value.employee_profile_id,
    roadmapId: value.roadmap_id,
    notes: value.notes,
    completedSteps: strings(value.completed_steps),
    normalizedMilestoneKeys: strings(value.normalized_milestone_keys),
    newGoals: strings(value.new_goals),
    updatedRecommendations: array(value.updated_recommendations).map((item) =>
      toBrowserRoadmapMilestone(object(item))),
    createdAt: value.created_at,
  };
}

function toBrowserNextAction(value: JsonObject): JsonObject {
  return {
    kind: value.kind,
    title: value.title,
    reason: value.reason,
    target: value.target,
  };
}

export function toBrowserProgressReview(value: JsonObject): JsonObject {
  return {
    revision: toBrowserRevision(object(value.revision)),
    presentation: value.presentation,
    followUpPrompt: value.follow_up_prompt,
    checkIn: toBrowserCheckIn(object(value.check_in)),
    roadmapId: value.roadmap_id,
    currentStatus: value.current_status,
    gaps: strings(value.gaps),
    milestones: array(value.milestones).map((item) => toBrowserRoadmapMilestone(object(item))),
    nextAction: toBrowserNextAction(object(value.next_action)),
  };
}

function browserFieldName(value: string): string {
  return value.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase());
}

export function toBrowserProgressProblem(value: JsonObject): JsonObject {
  const fieldErrors = object(value.field_errors);
  return {
    type: value.type ?? "about:blank",
    title: value.title ?? "Progress operation failed",
    status: value.status ?? 500,
    code: value.code ?? "CORE_UNAVAILABLE",
    detail: value.detail ?? null,
    traceId: value.correlation_id ?? "unknown",
    retryable: value.retryable ?? false,
    fieldErrors: Object.entries(fieldErrors).map(([field, messages]) => ({
      field: browserFieldName(field),
      messages: strings(messages),
    })),
  };
}
