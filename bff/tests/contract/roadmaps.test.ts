import { describe, expect, it } from "vitest";
import { toBrowserRoadmapResult, toCoreRoadmapRequest } from "../../src/contracts/roadmap.js";

describe("roadmap mapping", () => {
  it("maps the browser request only through the declared core shape", () => {
    expect(toCoreRoadmapRequest({ employeeProfile: { role: "Administrator", experienceLevel: "beginner", targetRole: "DevOps Engineer", availableTimePerWeek: 5 } })).toMatchObject({
      employee_profile: { role: "Administrator", experience_level: "beginner", target_role: "DevOps Engineer", available_time_per_week: 5 },
      clarifying_questions_asked: 0,
    });
  });
  it("preserves ready versus needs-more-info discrimination", () => {
    expect(toBrowserRoadmapResult({ status: "ready", roadmap: { id: "one" } })).toMatchObject({ status: "ready", roadmap: { id: "one" } });
    expect(toBrowserRoadmapResult({ status: "needs_more_info", clarifying_questions: [{ prompt: "Role?" }] })).toMatchObject({ status: "needsMoreInfo", clarifyingQuestions: [{ prompt: "Role?" }] });
  });
});
