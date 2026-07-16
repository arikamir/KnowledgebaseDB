import { describe, expect, it, vi } from "vitest";
import { approveSessionActivation } from "../../src/auth/lifecycle-gate.js";

describe("callback lifecycle gate", () => {
  it("approves only an active core result", async () => {
    const bootstrap = vi.fn(async () => ({ status: "active" as const, employeeId: "employee" }));
    await expect(approveSessionActivation({ bootstrap }, "tenant", "subject")).resolves.toBe("employee");
    expect(bootstrap).toHaveBeenCalledOnce();
  });

  it.each(["departed", "unknown"] as const)("rejects %s without session activation", async (status) => {
    await expect(approveSessionActivation({ bootstrap: async () => ({ status }) }, "tenant", "subject")).rejects.toThrow();
  });

  it("maps core outage without session activation", async () => {
    await expect(approveSessionActivation({ bootstrap: async () => { throw new Error("offline"); } }, "tenant", "subject")).rejects.toThrow("CORE_UNAVAILABLE");
  });
});
