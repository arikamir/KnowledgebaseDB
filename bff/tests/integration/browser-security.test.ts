import { afterEach, describe, expect, it } from "vitest";
import { buildApp } from "../../src/app.js";
import { loadConfig } from "../../src/config.js";
import { EncryptionKeyRing } from "../../src/sessions/encryption-key-ring.js";
import { EncryptedSessionStore, type SessionData } from "../../src/sessions/session-store.js";
import { MemorySessionBackend } from "../helpers/session.js";

const apps: ReturnType<typeof buildApp>[] = [];
afterEach(async () => { await Promise.all(apps.splice(0).map((app) => app.close())); });

async function securedApp() {
  const backend = new MemorySessionBackend();
  const sessions = new EncryptedSessionStore(
    backend,
    new EncryptionKeyRing([{ version: "v1", key: Buffer.alloc(32, 1), mode: "active" }]),
  );
  const now = new Date();
  const session: SessionData = {
    sessionId: "opaque-session-value",
    ownerKey: "tenant:owner",
    csrfToken: "csrf-secret-value",
    issuedAt: now.toISOString(),
    lastSeenAt: now.toISOString(),
    idleExpiresAt: new Date(now.getTime() + 30 * 60_000).toISOString(),
    absoluteExpiresAt: new Date(now.getTime() + 8 * 60 * 60_000).toISOString(),
  };
  await sessions.save(session);
  const app = buildApp(loadConfig({ PUBLIC_ORIGIN: "https://app.test" }));
  apps.push(app);
  Object.assign(app, { authServices: { sessions, publicOrigin: "https://app.test" } });
  return app;
}

describe("browser security boundary", () => {
  it("sets a deny-by-default CSP and defensive browser headers", async () => {
    const app = await securedApp();
    const response = await app.inject({ method: "GET", url: "/health/live" });

    expect(response.headers["content-security-policy"]).toContain("default-src 'none'");
    expect(response.headers["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(response.headers["x-content-type-options"]).toBe("nosniff");
    expect(response.headers["referrer-policy"]).toBe("no-referrer");
  });

  it.each([
    { name: "missing Origin", status: 400, headers: { "x-csrf-token": "csrf-secret-value" } },
    { name: "foreign Origin", status: 403, headers: { origin: "https://evil.test", "x-csrf-token": "csrf-secret-value" } },
    { name: "missing CSRF", status: 403, headers: { origin: "https://app.test" } },
    { name: "wrong CSRF", status: 403, headers: { origin: "https://app.test", "x-csrf-token": "wrong-secret-value" } },
  ])("denies active-session logout with $name without reflecting credentials", async ({ headers, status }) => {
    const app = await securedApp();
    const response = await app.inject({
      method: "POST",
      url: "/bff/v1/auth/logout",
      headers: { ...headers, authorization: "Bearer browser-secret-token" },
      cookies: { "__Host-learning_session": "opaque-session-value" },
    });

    expect(response.statusCode).toBe(status);
    expect(response.body).not.toContain("browser-secret-token");
    expect(response.body).not.toContain("opaque-session-value");
    expect(response.body).not.toContain("csrf-secret-value");
    expect(response.headers["set-cookie"]).toBeUndefined();
  });

  it("clears the host-only cookie only after exact Origin and CSRF validation", async () => {
    const app = await securedApp();
    const response = await app.inject({
      method: "POST",
      url: "/bff/v1/auth/logout",
      headers: { origin: "https://app.test", "x-csrf-token": "csrf-secret-value" },
      cookies: { "__Host-learning_session": "opaque-session-value" },
    });

    expect(response.statusCode).toBe(303);
    const cookie = response.headers["set-cookie"] as string;
    expect(cookie).toContain("__Host-learning_session=");
    expect(cookie).toContain("Path=/");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("Secure");
    expect(cookie).toContain("SameSite=Lax");
    expect(cookie).toContain("Max-Age=0");
    expect(cookie).not.toContain("Domain=");
    expect(cookie).not.toContain("opaque-session-value");
  });
});
