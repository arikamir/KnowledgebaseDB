import { bffRequest } from "../bff/client";
import { currentTopic, nextAction, normalizeMilestones } from "./learner-state-mappers";
import type { LearnerState } from "../contracts/learner-state";
import { learnerFixture } from "../mocks/learner-fixture";

export async function fetchLearnerSnapshot(): Promise<Pick<LearnerState, "roadmap" | "milestones" | "currentTopic" | "nextAction" | "status" | "error" | "lastUpdatedAt">> {
  if (import.meta.env.DEV && window.location.hostname === "127.0.0.1") { const milestones = learnerFixture.milestones; const topic = currentTopic(milestones); return { roadmap: learnerFixture, milestones, currentTopic: topic, nextAction: nextAction(topic), status: "ready", error: null, lastUpdatedAt: new Date().toISOString() }; }
  try { const roadmaps = await bffRequest<Array<Record<string, unknown>>>("/bff/v1/roadmaps"); const roadmap = roadmaps[0] ?? null; const milestones = normalizeMilestones((roadmap?.milestones as Array<Record<string, unknown>> | undefined) ?? []); const topic = currentTopic(milestones); return { roadmap, milestones, currentTopic: topic, nextAction: nextAction(topic), status: milestones.length ? "ready" : "empty", error: null, lastUpdatedAt: new Date().toISOString() }; } catch (error) { return { roadmap: null, milestones: [], currentTopic: null, nextAction: null, status: "unavailable", error: { code: "CORE_UNAVAILABLE", message: error instanceof Error ? error.message : "Service unavailable", retryable: true }, lastUpdatedAt: null }; }
}
