import { describe, expect, it } from "vitest";
import { EncryptionKeyRing } from "../../src/sessions/encryption-key-ring.js";
import { EncryptedSessionStore, SessionDependencyUnavailable } from "../../src/sessions/session-store.js";
import { MemorySessionBackend } from "../helpers/session.js";
import { RedisSessionBackend, type RedisConnection } from "../../src/sessions/redis-session-backend.js";

describe("Redis Entra/session dependency behavior", () => {
  it("uses bounded 100/500ms retries and fails indeterminate without fabrication", async () => {
    const backend = new MemorySessionBackend(); backend.fail = true;
    const delays: number[] = [];
    const store = new EncryptedSessionStore(backend, new EncryptionKeyRing([{ version: "v1", key: Buffer.alloc(32, 1), mode: "active" }]), async (delay) => { delays.push(delay); });
    await expect(store.load("opaque")).rejects.toBeInstanceOf(SessionDependencyUnavailable);
    expect(backend.calls).toBe(3);
    expect(delays).toEqual([100, 500]);
  });

  it("acquires a new Entra token on reconnect without an access-key fallback", async () => {
    const tokens = ["entra-token-1", "entra-token-2"];
    const used: string[] = [];
    const values = new Map<string, string>();
    const connection = (): RedisConnection => ({
      get: async (key) => values.get(key) ?? null,
      set: async (key, value) => { values.set(key, value); },
      del: async (key) => { values.delete(key); },
      sadd: async () => 1,
      smembers: async () => [],
      quit: async () => undefined,
    });
    const backend = new RedisSessionBackend({
      acquireToken: async () => tokens.shift() ?? "",
      connect: async (token) => { used.push(token); return connection(); },
    });
    await backend.set("session:a", "one");
    await backend.reconnect();
    expect(used).toEqual(["entra-token-1", "entra-token-2"]);
  });
});
