import { describe, expect, it } from "vitest";
import {
  guidanceCatalogCompatible,
  toBrowserGuidanceProblem,
  toBrowserGuidanceResult,
  toCoreGuidanceRequest,
} from "../../src/contracts/guidance.js";

describe("guidance contract mapping", () => {
  it("preserves the requested topic and maps profile fields without substitution", () => {
    expect(toCoreGuidanceRequest({
      topic: " K8S ",
      employeeProfile: { role: "Administrator", experienceLevel: "beginner", targetRole: "Platform engineer" },
    })).toMatchObject({
      topic: " K8S ",
      employee_profile: { role: "Administrator", experience_level: "beginner", target_role: "Platform engineer" },
    });
  });

  it("maps requested and canonical resolved topics, cost status, and only safe active labs", () => {
    const result = toBrowserGuidanceResult({
      requested_topic: "K8S", resolved_topic: "Kubernetes", supported: true,
      topic_summary: "summary", current_level_fit: "fit", practical_next_action: "next",
      common_pitfalls: [], related_topics: [], suggestions: [], notes: [],
      lab_references: [
        { id: "active", provider: "Docs", objective: "Try", prerequisites: [], estimated_minutes: 20, cost_status: "free", destination_url: "https://example.test", availability_status: "active" },
        { id: "retired", provider: "Old", objective: "Skip", prerequisites: [], estimated_minutes: 20, cost_status: "paid", destination_url: "https://example.test", availability_status: "retired" },
      ],
    });
    expect(result).toMatchObject({ requestedTopic: "K8S", resolvedTopic: "Kubernetes", labReferences: [{ id: "active", costStatus: "free", availabilityStatus: "active" }, { id: "retired", availabilityStatus: "retired" }] });
  });

  it.each([
    ["GUIDANCE_TOPIC_UNAVAILABLE", true],
    ["GUIDANCE_TOPIC_UNAVAILABLE", false],
    ["GUIDANCE_TOPIC_UNINTERPRETABLE", false],
    ["VALIDATION_FAILED", false],
    ["CAPABILITY_METADATA_UNAVAILABLE", true],
    ["CORE_UNAVAILABLE", true],
  ])("preserves stable %s problems and retryability", (code, retryable) => {
    expect(toBrowserGuidanceProblem({ status: code.endsWith("UNAVAILABLE") && code.startsWith("GUIDANCE") ? 422 : 503, code, retryable, field_errors: { topic: ["message"] }, correlation_id: "trace" })).toMatchObject({ code, retryable, fieldErrors: [{ field: "topic", messages: ["message"] }], traceId: "trace" });
  });

  it("treats a catalog mismatch as compatibility, not as a topic error", () => {
    expect(guidanceCatalogCompatible("1.0.0")).toBe(true);
    expect(guidanceCatalogCompatible("2.0.0")).toBe(false);
  });
});
