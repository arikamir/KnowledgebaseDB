import { describe, expect, it, vi } from "vitest";
import { CoreCapabilityPolicy, type CoreCapabilities } from "../../src/compatibility/core-version.js";

const capabilities: CoreCapabilities = { contractVersion: "1.0.0", supportedContractVersions: ["1.0.0"], catalogVersion: "1.0.0", mutations: ["createRoadmap"] };

describe("core capability cache", () => {
  it("single-flights at 45 seconds and gates mutations at 60 seconds", async () => {
    let now = 0;
    const fetcher = vi.fn(async () => capabilities);
    const policy = new CoreCapabilityPolicy(fetcher, () => now);
    await Promise.all([policy.safeRead(), policy.safeRead()]);
    expect(fetcher).toHaveBeenCalledOnce();
    now = 46_000;
    await Promise.all([policy.safeRead(), policy.safeRead()]);
    expect(fetcher).toHaveBeenCalledTimes(2);
    now = 61_000;
    await policy.requireMutation("createRoadmap");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("keeps a last valid entry for read diagnosis but never fabricates a mutation", async () => {
    let now = 0;
    const fetcher = vi.fn().mockResolvedValueOnce(capabilities).mockRejectedValue(new Error("offline"));
    const policy = new CoreCapabilityPolicy(fetcher, () => now);
    await policy.safeRead();
    now = 120_000;
    await expect(policy.safeRead()).resolves.toEqual(capabilities);
    await expect(policy.requireMutation("otherMutation")).rejects.toThrow();
  });
});
