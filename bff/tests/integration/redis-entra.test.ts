import { describe, expect, it } from "vitest";
import { EncryptionKeyRing } from "../../src/sessions/encryption-key-ring.js";
import { EncryptedSessionStore, SessionDependencyUnavailable } from "../../src/sessions/session-store.js";
import { MemorySessionBackend } from "../helpers/session.js";

describe("Redis Entra/session dependency behavior", () => {
  it("uses bounded 100/500ms retries and fails indeterminate without fabrication", async () => {
    const backend = new MemorySessionBackend(); backend.fail = true;
    const delays: number[] = [];
    const store = new EncryptedSessionStore(backend, new EncryptionKeyRing([{ version: "v1", key: Buffer.alloc(32, 1), mode: "active" }]), async (delay) => { delays.push(delay); });
    await expect(store.load("opaque")).rejects.toBeInstanceOf(SessionDependencyUnavailable);
    expect(backend.calls).toBe(3);
    expect(delays).toEqual([100, 500]);
  });
});
