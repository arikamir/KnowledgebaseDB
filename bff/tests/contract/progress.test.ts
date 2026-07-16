import Fastify, { type FastifyInstance } from "fastify";
import { afterEach, describe, expect, it } from "vitest";
import {
  toBrowserProgressProblem,
  toBrowserProgressReview,
  toCoreProgressCheckIn,
} from "../../src/contracts/progress.js";
import { installGeneratedSchemas } from "../../src/plugins/generated-validation.js";
import { progressRoutes } from "../../src/routes/progress.js";

const timestamp = "2026-07-16T12:00:00Z";
const coreMilestone = {
  id: "milestone-1",
  milestone_key: "linux-foundations-001",
  ordinal: 0,
  title: "Build Linux foundations",
  skill_area: "Linux",
  experience_level_fit: "intermediate",
  time_horizon: "immediate",
  concrete_next_action: "Complete one lab",
  reason_it_matters: "Builds operational fluency",
  priority: 1,
  completion_state: "pending",
  supporting_notes: [],
};
const coreRoadmap = {
  id: "roadmap-1",
  owner_type: "employee",
  employee_profile_id: "profile-1",
  previous_roadmap_id: null,
  goal_summary: "Move toward DevOps",
  current_focus: "Build Linux foundations",
  milestones: [coreMilestone],
  next_actions: [coreMilestone],
  status: "revised",
  assumptions: [],
  clarifying_questions_asked: 0,
  created_at: timestamp,
  updated_at: timestamp,
};
const coreReview = {
  revision: {
    prior_roadmap: coreRoadmap,
    updated_roadmap: coreRoadmap,
    completed_steps: [],
    normalized_milestone_keys: [],
    new_goals: [],
    summary: "Progress check-in recorded.",
    created_at: timestamp,
  },
  presentation: "Progress recorded.",
  follow_up_prompt: "Continue the next milestone.",
  check_in: {
    id: "check-in-1",
    owner_type: "employee",
    employee_profile_id: "profile-1",
    roadmap_id: "roadmap-1",
    notes: "Keep these notes",
    completed_steps: [],
    normalized_milestone_keys: [],
    new_goals: [],
    updated_recommendations: [coreMilestone],
    created_at: timestamp,
  },
  roadmap_id: "roadmap-1",
  current_status: "in_progress",
  gaps: ["Build Linux foundations"],
  milestones: [coreMilestone],
  next_action: {
    kind: "continue_milestone",
    title: "Build Linux foundations",
    reason: "Continue the next incomplete milestone.",
    target: "linux-foundations-001",
  },
};

const apps: FastifyInstance[] = [];
afterEach(async () => Promise.all(apps.splice(0).map((app) => app.close())));

async function progressApp(core: (path: string, init: RequestInit) => Promise<Response>, logs?: string[]) {
  const app = Fastify(logs ? { logger: { stream: { write: (message: string) => { logs.push(message); } } } } : undefined);
  apps.push(app);
  installGeneratedSchemas(app);
  Object.assign(app, { progressServices: { core } });
  await app.register(progressRoutes);
  await app.ready();
  return app;
}

const browserHeaders = {
  origin: "https://app.test",
  "x-ui-contract-version": "1.0.0",
  "x-csrf-token": "csrf-token-value-0001",
  "idempotency-key": "progress-action-key-0001",
};

describe("progress generated contract and mapping", () => {
  it("maps only declared browser fields to the core request", () => {
    expect(toCoreProgressCheckIn({
      employeeProfileId: "compatibility-only",
      roadmapId: "roadmap-1",
      notes: "Keep these notes",
      completedSteps: ["Linux"],
      completedMilestoneKeys: ["linux-foundations-001"],
      newGoals: ["GitOps"],
    })).toEqual({
      employee_profile_id: "compatibility-only",
      roadmap_id: "roadmap-1",
      notes: "Keep these notes",
      completed_steps: ["Linux"],
      completed_milestone_keys: ["linux-foundations-001"],
      new_goals: ["GitOps"],
    });
  });

  it("maps the complete review recursively without exposing core ownership fields", () => {
    const mapped = toBrowserProgressReview(coreReview);
    expect(mapped).toMatchObject({
      roadmapId: "roadmap-1",
      currentStatus: "in_progress",
      revision: {
        priorRoadmap: { employeeProfileId: "profile-1" },
        normalizedMilestoneKeys: [],
      },
      checkIn: { employeeProfileId: "profile-1", notes: "Keep these notes" },
      milestones: [{ milestoneKey: "linux-foundations-001", skillArea: "Linux" }],
      nextAction: { kind: "continue_milestone", target: "linux-foundations-001" },
    });
    expect(JSON.stringify(mapped)).not.toContain("owner_type");
    expect(JSON.stringify(mapped)).not.toContain("next_actions");
  });

  it("maps stable core problems and field errors", () => {
    expect(toBrowserProgressProblem({
      type: "https://example.test/problems/validation",
      title: "Rejected",
      status: 422,
      code: "MILESTONE_KEY_UNKNOWN",
      detail: "Unknown milestone",
      correlation_id: "trace-1",
      retryable: false,
      field_errors: { completed_milestone_keys: ["Unknown key"] },
    })).toEqual({
      type: "https://example.test/problems/validation",
      title: "Rejected",
      status: 422,
      code: "MILESTONE_KEY_UNKNOWN",
      detail: "Unknown milestone",
      traceId: "trace-1",
      retryable: false,
      fieldErrors: [{ field: "completedMilestoneKeys", messages: ["Unknown key"] }],
    });
  });

  it("rejects an invalid generated-schema request before calling core", async () => {
    let calls = 0;
    const app = await progressApp(async () => {
      calls += 1;
      return Response.json(coreReview);
    });

    const missingRoadmap = await app.inject({
      method: "POST",
      url: "/bff/v1/progress/check-ins",
      headers: browserHeaders,
      payload: { notes: "Missing roadmap" },
    });
    const invalidKey = await app.inject({
      method: "POST",
      url: "/bff/v1/progress/check-ins",
      headers: browserHeaders,
      payload: { roadmapId: "roadmap-1", completedMilestoneKeys: ["NOT-VALID"] },
    });
    const missingKeyHeaders: Record<string, string> = { ...browserHeaders };
    delete missingKeyHeaders["idempotency-key"];
    const missingIntendedActionKey = await app.inject({
      method: "POST",
      url: "/bff/v1/progress/check-ins",
      headers: missingKeyHeaders,
      payload: { roadmapId: "roadmap-1" },
    });
    const missingReviewRoadmap = await app.inject({
      method: "GET",
      url: "/bff/v1/progress/reviews",
    });

    expect(missingRoadmap.statusCode).toBe(422);
    expect(missingRoadmap.json()).toMatchObject({
      code: "VALIDATION_FAILED",
      fieldErrors: [{ field: "roadmapId" }],
    });
    expect(invalidKey.statusCode).toBe(422);
    expect(missingIntendedActionKey.statusCode).toBe(422);
    expect(missingIntendedActionKey.json()).toMatchObject({
      fieldErrors: [{ field: "idempotencyKey" }],
    });
    expect(missingReviewRoadmap.statusCode).toBe(422);
    expect(calls).toBe(0);
  });

  it("forwards the exact intended-action key and maps exact core replay", async () => {
    const calls: Array<{ path: string; init: RequestInit }> = [];
    const app = await progressApp(async (path, init) => {
      calls.push({ path, init });
      return Response.json(coreReview);
    });
    const request = {
      method: "POST" as const,
      url: "/bff/v1/progress/check-ins",
      headers: browserHeaders,
      payload: { roadmapId: "roadmap-1", notes: "Keep these notes" },
    };

    const created = await app.inject(request);
    const replayed = await app.inject(request);

    expect(created.statusCode).toBe(200);
    expect(replayed.json()).toEqual(created.json());
    expect(calls).toHaveLength(2);
    expect(calls.map(({ path }) => path)).toEqual([
      "/api/v1/progress/check-ins",
      "/api/v1/progress/check-ins",
    ]);
    expect(calls.map(({ init }) => new Headers(init.headers).get("Idempotency-Key"))).toEqual([
      browserHeaders["idempotency-key"],
      browserHeaders["idempotency-key"],
    ]);
    expect(calls.every(({ init }) => Boolean(new Headers(init.headers).get("X-Correlation-ID")))).toBe(true);
  });

  it("loads and maps the latest employee review by encoded roadmap query", async () => {
    const paths: string[] = [];
    const app = await progressApp(async (path) => {
      paths.push(path);
      return Response.json(coreReview);
    });

    const response = await app.inject({
      method: "GET",
      url: "/bff/v1/progress/reviews?roadmapId=roadmap%2Fone",
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({ roadmapId: "roadmap-1", checkIn: { id: "check-in-1" } });
    expect(paths).toEqual(["/api/v1/progress/reviews?roadmap_id=roadmap%2Fone"]);
  });

  it("emits allowlisted success and denial telemetry without personalized values", async () => {
    const logs: string[] = [];
    let call = 0;
    const app = await progressApp(async () => {
      call += 1;
      return call === 1
        ? Response.json(coreReview)
        : Response.json({
          type: "https://example.test/problems/not-found", title: "Not found", status: 404,
          code: "ROADMAP_NOT_FOUND", correlation_id: "core-trace", retryable: false, field_errors: {},
        }, { status: 404 });
    }, logs);
    const request = {
      method: "POST" as const,
      url: "/bff/v1/progress/check-ins",
      headers: browserHeaders,
      payload: { roadmapId: "roadmap-1", notes: "private-note-value" },
    };

    await app.inject(request);
    await app.inject(request);

    const telemetry = logs
      .map((line) => JSON.parse(line) as Record<string, unknown>)
      .filter((entry) => entry.msg === "progress request completed");
    expect(telemetry).toHaveLength(2);
    expect(telemetry[0]).toMatchObject({ routeClass: "progress_mutation", outcome: "success", statusCode: 200 });
    expect(telemetry[1]).toMatchObject({ routeClass: "progress_mutation", outcome: "denied", statusCode: 404, denialCode: "ROADMAP_NOT_FOUND" });
    const encoded = JSON.stringify(telemetry);
    expect(encoded).not.toContain("private-note-value");
    expect(encoded).not.toContain(browserHeaders["idempotency-key"]);
    expect(encoded).not.toContain("roadmap-1");
  });
});
