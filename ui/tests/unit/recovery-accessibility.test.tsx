import { describe, expect, it } from "vitest";
import { achievementTier } from "../../src/app/learner-state-mappers";
describe("recovery and accessibility policy", () => { it("keeps the passing threshold at 80%", () => { expect(achievementTier(80)).toBe("bronze"); expect(achievementTier(79)).toBeNull(); }); });
