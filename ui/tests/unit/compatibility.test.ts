import { describe, expect, it, vi } from "vitest";
import { CapabilityPolicy } from "../../src/app/compatibility";
import type { CapabilityMetadata } from "../../src/contracts/bff-api";

const metadata: CapabilityMetadata = {
  contractVersion: "1.0.0", catalogVersion: "1.0.0", status: "compatible",
  generatedAt: "2026-07-16T00:00:00Z", supportedContractVersions: ["1.0.0"], supportedMutations: ["createRoadmap"],
};

describe("capability policy", () => {
  it("single-flights refresh and permits mutations only inside 60 seconds", async () => {
    const fetcher = vi.fn(async () => metadata);
    const policy = new CapabilityPolicy(fetcher, () => 1_000);
    await Promise.all([policy.forMutation(), policy.forMutation()]);
    expect(fetcher).toHaveBeenCalledOnce();
  });
});
