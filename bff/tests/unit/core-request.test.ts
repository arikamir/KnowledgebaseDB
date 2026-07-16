import { describe, expect, it, vi } from "vitest";
import { coreRequest } from "../../src/clients/core-request.js";

describe("core request policy", () => {
  it("retries safe reads twice at 250ms and one second", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(new Response(null, { status: 503 })).mockResolvedValueOnce(new Response(null, { status: 503 })).mockResolvedValue(new Response("{}", { status: 200 }));
    const delays: number[] = [];
    expect((await coreRequest(new URL("https://core.test/api/v1/capabilities"), { method: "GET" }, fetcher, async (delay) => { delays.push(delay); })).status).toBe(200);
    expect(delays).toEqual([250, 1000]);
  });

  it("retries a dispatched mutation only once with the same key", async () => {
    const fetcher = vi.fn().mockRejectedValueOnce(new Error("timeout")).mockResolvedValue(new Response("{}", { status: 200 }));
    await coreRequest(new URL("https://core.test/api/v1/roadmaps"), { method: "POST", mutationDispatched: true, idempotencyKey: "same-key" }, fetcher, async () => {});
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect((fetcher.mock.calls[0][1]!.headers as Record<string, string>)["Idempotency-Key"]).toBe("same-key");
    expect((fetcher.mock.calls[1][1]!.headers as Record<string, string>)["Idempotency-Key"]).toBe("same-key");
  });
});
