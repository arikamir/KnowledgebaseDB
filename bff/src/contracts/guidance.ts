import { GUIDANCE_CATALOG_VERSION } from "./supported-guidance-topics.js";

export interface BrowserGuidanceRequest {
  topic: string;
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
  requestText?: string | null;
}

interface CoreProblem {
  type?: string;
  title?: string;
  status?: number;
  code?: string;
  detail?: string | null;
  retryable?: boolean;
  field_errors?: Record<string, string[]>;
  correlation_id?: string;
}

interface CoreLabReference {
  id: string;
  provider: string;
  objective: string;
  prerequisites: string[];
  estimated_minutes: number;
  cost_status: "free" | "paid" | "subscription" | "unknown";
  destination_url: string;
  availability_status?: "active" | "unavailable" | "retired";
}

export function toCoreGuidanceRequest(request: BrowserGuidanceRequest): object {
  return {
    topic: request.topic,
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
  };
}

export function toBrowserGuidanceResult(value: Record<string, unknown>): Record<string, unknown> {
  const labs = Array.isArray(value.lab_references) ? value.lab_references as CoreLabReference[] : [];
  return {
    requestedTopic: value.requested_topic,
    resolvedTopic: value.resolved_topic,
    supported: value.supported,
    topicSummary: value.topic_summary,
    currentLevelFit: value.current_level_fit,
    practicalNextAction: value.practical_next_action,
    labReferences: labs
      .filter((lab) => lab.destination_url.startsWith("https://"))
      .map((lab) => ({
        id: lab.id,
        provider: lab.provider,
        objective: lab.objective,
        prerequisites: lab.prerequisites,
        estimatedMinutes: lab.estimated_minutes,
        costStatus: lab.cost_status,
        availabilityStatus: lab.availability_status ?? "active",
        destinationUrl: lab.destination_url,
      })),
    suggestions: value.suggestions ?? [],
    commonPitfalls: value.common_pitfalls ?? [],
    relatedTopics: value.related_topics ?? [],
    notes: value.notes ?? [],
  };
}

export function toBrowserGuidanceProblem(problem: CoreProblem): Record<string, unknown> {
  const fieldErrors = Object.entries(problem.field_errors ?? {}).map(([field, messages]) => ({ field, messages }));
  return {
    type: problem.type ?? "about:blank",
    title: problem.title ?? "Guidance request failed",
    status: problem.status ?? 500,
    code: problem.code ?? "CORE_UNAVAILABLE",
    detail: problem.detail ?? null,
    retryable: problem.retryable ?? false,
    fieldErrors,
    traceId: problem.correlation_id ?? "unknown",
  };
}

export function guidanceCatalogCompatible(version: string | undefined): boolean {
  return version === undefined || version === GUIDANCE_CATALOG_VERSION;
}
