import { describe, expect, it } from "vitest";
import { initialLearnerState, learnerStateReducer } from "../../src/app/learner-state-context";
import { achievementTier, normalizeMilestones } from "../../src/app/learner-state-mappers";

describe("learner state", () => {
  it("derives mutually exclusive achievement tiers", () => { expect(achievementTier(79)).toBeNull(); expect(achievementTier(80)).toBe("bronze"); expect(achievementTier(90)).toBe("silver"); expect(achievementTier(95)).toBe("gold"); });
  it("normalizes roadmap milestones and preserves completion state", () => { expect(normalizeMilestones([{ milestone_key: "m", title: "Milestone", completion_state: "completed", score: 91 }])[0]).toMatchObject({ milestoneKey: "m", completionState: "completed", achievementTier: "silver" }); });
  it("preserves a draft on delivery failure and clears it only after success", () => { const pending = learnerStateReducer(initialLearnerState, { type: "pending", message: { id: "u", role: "user", text: "question", createdAt: "now" } }); const failed = learnerStateReducer(pending, { type: "failed", error: { code: "503", message: "retry", retryable: true } }); expect(failed.conversation.messages).toHaveLength(1); const delivered = learnerStateReducer(failed, { type: "delivered", message: { id: "a", role: "assistant", text: "answer", createdAt: "now" } }); expect(delivered.conversation.deliveryState).toBe("delivered"); });
  it("invalidates user state on auth epoch reset", () => { const state = learnerStateReducer(initialLearnerState, { type: "draft", value: "private" }); expect(learnerStateReducer(state, { type: "invalidate" }).conversation.draft).toBe(""); });
});
