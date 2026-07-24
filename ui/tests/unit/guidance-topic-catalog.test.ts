import { describe, expect, it } from "vitest";
import { GUIDANCE_CATALOG_VERSION, GUIDANCE_TOPICS } from "../../src/contracts/supported-guidance-topics";

describe("UI guidance catalog", () => {
  it("keeps generated canonical IDs and explicit lifecycle states", () => {
    expect(GUIDANCE_CATALOG_VERSION).toBe("1.0.0");
    expect(GUIDANCE_TOPICS.find((topic) => topic.aliases.some((alias) => alias === "k8s"))?.id).toBe("kubernetes");
  });
});
