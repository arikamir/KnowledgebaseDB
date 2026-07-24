import { describe, expect, it } from "vitest";
import { CORE_CONTRACT_DIGEST, CORE_OPERATIONS } from "../../src/contracts/core-api.js";

describe("core client contract", () => {
  it("binds the canonical digest and operation inventory", () => {
    expect(CORE_CONTRACT_DIGEST).toMatch(/^[a-f0-9]{64}$/);
    expect(new Set(CORE_OPERATIONS.map((operation) => operation.operationId)).size).toBe(CORE_OPERATIONS.length);
  });
});
