import { afterEach, describe, expect, it } from "vitest";
import { buildApp } from "../../src/app.js";
import { loadConfig } from "../../src/config.js";
import { canonicalizeReturnTarget } from "../../src/auth/entra.js";
import { EncryptionKeyRing } from "../../src/sessions/encryption-key-ring.js";
import { EncryptedSessionStore, type SessionData } from "../../src/sessions/session-store.js";
import { MemorySessionBackend } from "../helpers/session.js";

const apps: ReturnType<typeof buildApp>[] = [];
afterEach(async () => { await Promise.all(apps.splice(0).map((app) => app.close())); });

describe("browser authentication session", () => {
  it.each(["https://evil.test", "//evil.test", "/\\evil", "/%2f%2fevil", "/ok#fragment", "/bad\u0000"])("canonicalizes unsafe return target %s", (value) => {
    expect(canonicalizeReturnTarget(value)).toBe("/");
  });

  it("preserves a safe relative target", () => { expect(canonicalizeReturnTarget("/roadmaps?view=current")).toBe("/roadmaps?view=current"); });

  it("uses 302 for authorization and an opaque host-only state cookie", async () => {
    const app = buildApp(loadConfig({})); apps.push(app);
    Object.assign(app, { authServices: { publicOrigin: "https://app.test", authorizationUrl: "https://login.test/authorize" } });
    const response = await app.inject({ method: "GET", url: "/bff/v1/auth/login?return_to=%2Froadmaps" });
    expect(response.statusCode).toBe(302);
    expect(response.headers.location).toContain("https://login.test/authorize?");
    const cookie = response.headers["set-cookie"] as string;
    expect(cookie).toContain("__Host-learning_auth_state=");
    expect(cookie).toContain("HttpOnly"); expect(cookie).toContain("Secure"); expect(cookie).toContain("SameSite=Lax");
  });

  it("does not clear a cookie when Redis state is indeterminate", async () => {
    const backend = new MemorySessionBackend(); backend.fail = true;
    const sessions = new EncryptedSessionStore(backend, new EncryptionKeyRing([{ version: "v1", key: Buffer.alloc(32, 1), mode: "active" }]), async () => {});
    const app = buildApp(loadConfig({})); apps.push(app);
    Object.assign(app, { authServices: { sessions, publicOrigin: "https://app.test" } });
    const response = await app.inject({ method: "GET", url: "/bff/v1/session", cookies: { "__Host-learning_session": "opaque" } });
    expect(response.statusCode).toBe(503);
    expect(response.headers["set-cookie"]).toBeUndefined();
  });

  it("requires exact Origin and CSRF for active logout, then clears with 303", async () => {
    const backend = new MemorySessionBackend();
    const sessions = new EncryptedSessionStore(backend, new EncryptionKeyRing([{ version: "v1", key: Buffer.alloc(32, 1), mode: "active" }]));
    const now = new Date();
    const csrfToken = "csrf-token-value-0001";
    const session: SessionData = { sessionId: "opaque", ownerKey: "tenant:owner", csrfToken, issuedAt: now.toISOString(), lastSeenAt: now.toISOString(), idleExpiresAt: new Date(now.getTime() + 1_000_000).toISOString(), absoluteExpiresAt: new Date(now.getTime() + 2_000_000).toISOString() };
    await sessions.save(session);
    const app = buildApp(loadConfig({})); apps.push(app);
    Object.assign(app, { authServices: { sessions, publicOrigin: "https://app.test" } });
    const denied = await app.inject({ method: "POST", url: "/bff/v1/auth/logout", headers: { origin: "https://evil.test", "x-csrf-token": csrfToken }, cookies: { "__Host-learning_session": "opaque" } });
    expect(denied.statusCode).toBe(403);
    const response = await app.inject({ method: "POST", url: "/bff/v1/auth/logout", headers: { origin: "https://app.test", "x-csrf-token": csrfToken }, cookies: { "__Host-learning_session": "opaque" } });
    expect(response.statusCode).toBe(303);
    expect(response.headers["set-cookie"]).toContain("Max-Age=0");
  });
});
