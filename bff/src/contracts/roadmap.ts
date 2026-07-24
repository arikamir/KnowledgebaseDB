export interface BrowserRoadmapCreateRequest {
  employeeProfile: {
    id?: string;
    role?: string;
    experienceLevel?: string;
    targetRole?: string;
    targetSpecializations?: string[];
    availableTimePerWeek?: number;
    learningPreferences?: string[];
    constraints?: string[];
  };
  requestText?: string;
  clarifyingQuestionsAsked?: number;
}

export function toCoreRoadmapRequest(request: BrowserRoadmapCreateRequest): object {
  return {
    employee_profile: {
      id: request.employeeProfile.id,
      role: request.employeeProfile.role,
      experience_level: request.employeeProfile.experienceLevel,
      target_role: request.employeeProfile.targetRole,
      target_specializations: request.employeeProfile.targetSpecializations ?? [],
      available_time_per_week: request.employeeProfile.availableTimePerWeek,
      learning_preferences: request.employeeProfile.learningPreferences ?? [],
      constraints: request.employeeProfile.constraints ?? [],
    },
    request_text: request.requestText,
    clarifying_questions_asked: request.clarifyingQuestionsAsked ?? 0,
  };
}

export function toBrowserRoadmapResult(value: Record<string, unknown>): Record<string, unknown> {
  return {
    status: value.status === "needs_more_info" ? "needsMoreInfo" : "ready",
    employeeProfileId: value.employee_profile_id,
    roadmapId: value.roadmap_id,
    roadmap: value.roadmap,
    clarifyingQuestions: value.clarifying_questions ?? [],
    assumptions: value.assumptions ?? [],
    presentation: value.presentation ?? "",
    followUpPrompt: value.follow_up_prompt ?? "",
  };
}

function array(value: unknown): unknown[] { return Array.isArray(value) ? value : []; }
function milestone(value: unknown): Record<string, unknown> {
  const item = value && typeof value === "object" ? value as Record<string, unknown> : {};
  return { id: item.id, milestoneKey: item.milestone_key ?? item.milestoneKey ?? item.id, ordinal: item.ordinal, title: item.title, skillArea: item.skill_area ?? item.skillArea, experienceLevelFit: item.experience_level_fit ?? item.experienceLevelFit, timeHorizon: item.time_horizon ?? item.timeHorizon, concreteNextAction: item.concrete_next_action ?? item.concreteNextAction, reasonItMatters: item.reason_it_matters ?? item.reasonItMatters, priority: item.priority, completionState: item.completion_state ?? item.completionState ?? item.status, supportingNotes: array(item.supporting_notes ?? item.supportingNotes).map(String), scorePercent: item.score_percent ?? item.scorePercent ?? item.score ?? null };
}
export function toBrowserRoadmap(value: unknown): Record<string, unknown> {
  const item = value && typeof value === "object" ? value as Record<string, unknown> : {};
  return { id: item.id, employeeProfileId: item.employee_profile_id ?? item.employeeProfileId, previousRoadmapId: item.previous_roadmap_id ?? item.previousRoadmapId ?? null, goalSummary: item.goal_summary ?? item.goalSummary, currentFocus: item.current_focus ?? item.currentFocus, milestones: array(item.milestones).map(milestone), status: item.status, assumptions: array(item.assumptions).map(String), clarifyingQuestionsAsked: item.clarifying_questions_asked ?? item.clarifyingQuestionsAsked ?? 0, createdAt: item.created_at ?? item.createdAt, updatedAt: item.updated_at ?? item.updatedAt };
}
export function toBrowserRoadmapList(value: unknown): Record<string, unknown>[] {
  const items: unknown[] = Array.isArray(value) ? value : (value && typeof value === "object" && Array.isArray((value as Record<string, unknown>).roadmaps) ? (value as Record<string, unknown>).roadmaps as unknown[] : []);
  return items.map(toBrowserRoadmap);
}
