import { describe, expect, it } from "vitest";
import { BFF_COMPONENT_SCHEMAS, BFF_ROUTE_SCHEMAS } from "../../src/contracts/bff-api.js";

describe("generated route schemas", () => {
  it("contains reusable components and every foundation operation schema", () => {
    expect(BFF_COMPONENT_SCHEMAS.length).toBeGreaterThan(10);
    for (const operation of ["getBffCapabilities", "getBrowserSession", "beginLogin", "completeLogin", "logout"] as const) {
      expect(BFF_ROUTE_SCHEMAS[operation]).toBeDefined();
    }
  });
});
