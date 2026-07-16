import { describe, expect, it } from "vitest";
import { EncryptionKeyRing } from "../../src/sessions/encryption-key-ring.js";
import { EncryptedSessionStore, type SessionData } from "../../src/sessions/session-store.js";
import { MemorySessionBackend } from "../helpers/session.js";

const session: SessionData = { sessionId: "session", ownerKey: "tenant:owner", csrfToken: "csrf", issuedAt: "2026-07-16T00:00:00Z", lastSeenAt: "2026-07-16T00:00:00Z", idleExpiresAt: "2026-07-16T00:30:00Z", absoluteExpiresAt: "2026-07-16T08:00:00Z" };

describe("session key rotation", () => {
  it("decrypts overlap keys and lazily rewrites with the active version", async () => {
    const backend = new MemorySessionBackend();
    const oldStore = new EncryptedSessionStore(backend, new EncryptionKeyRing([{ version: "old", key: Buffer.alloc(32, 1), mode: "active" }]));
    await oldStore.save(session);
    const rotating = new EncryptedSessionStore(backend, new EncryptionKeyRing([{ version: "new", key: Buffer.alloc(32, 2), mode: "active" }, { version: "old", key: Buffer.alloc(32, 1), mode: "decrypt_only" }]));
    expect(await rotating.load("session")).toEqual(session);
    expect(JSON.parse(backend.values.get("session:session")!).keyVersion).toBe("new");
  });

  it("rejects a retired key", () => {
    const old = new EncryptionKeyRing([{ version: "old", key: Buffer.alloc(32, 1), mode: "active" }]);
    const encrypted = old.encrypt(session);
    const current = new EncryptionKeyRing([{ version: "new", key: Buffer.alloc(32, 2), mode: "active" }]);
    expect(() => current.decrypt(encrypted)).toThrow("SESSION_KEY_RETIRED");
  });

  it("revokes every session indexed by a compromised key version", async () => {
    const backend = new MemorySessionBackend();
    const store = new EncryptedSessionStore(backend, new EncryptionKeyRing([{ version: "compromised", key: Buffer.alloc(32, 1), mode: "active" }]));
    await store.save(session);
    expect(await store.revokeKeyVersion("compromised")).toBe(1);
    expect(await store.load(session.sessionId)).toBeNull();
  });
});
