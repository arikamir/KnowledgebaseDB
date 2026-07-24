import { describe, expect, it } from "vitest";
import { toBrowserRoadmap, toBrowserRoadmapList, toBrowserRoadmapResult, toCoreRoadmapRequest } from "../../src/contracts/roadmap.js";

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
  it("normalizes core roadmap lists and resources to the browser contract", () => {
    const core = { id: "one", goal_summary: "Goal", milestones: [{ milestone_key: "m1", title: "First", completion_state: "in_progress", score_percent: 88, supporting_notes: ["note"] }] };
    expect(toBrowserRoadmapList([core])).toEqual([expect.objectContaining({ id: "one", goalSummary: "Goal", milestones: [expect.objectContaining({ milestoneKey: "m1", completionState: "in_progress", scorePercent: 88 })] })]);
    expect(toBrowserRoadmap(core)).toMatchObject({ id: "one", milestones: [{ milestoneKey: "m1" }] });
  });
});
