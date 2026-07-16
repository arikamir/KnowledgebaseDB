import { describe, expect, it } from "vitest";
import { GUIDANCE_CATALOG_VERSION, GUIDANCE_TOPICS } from "../../src/contracts/supported-guidance-topics.js";

describe("guidance topic catalog", () => {
  it("is versioned, unique, and uses explicit states", () => {
    expect(GUIDANCE_CATALOG_VERSION).toBe("1.0.0");
    expect(new Set(GUIDANCE_TOPICS.map((topic) => topic.id)).size).toBe(GUIDANCE_TOPICS.length);
    expect(GUIDANCE_TOPICS.every((topic) => ["active", "unavailable", "retired"].includes(topic.status))).toBe(true);
  });
});
