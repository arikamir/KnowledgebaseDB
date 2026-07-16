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
