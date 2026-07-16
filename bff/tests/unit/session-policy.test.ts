import { describe, expect, it } from "vitest";
import { evaluateSession } from "../../src/sessions/session-policy.js";
import type { SessionData } from "../../src/sessions/session-store.js";

const base: SessionData = {
  sessionId: "opaque", ownerKey: "tenant:owner", csrfToken: "csrf",
  issuedAt: "2026-07-16T09:00:00Z", lastSeenAt: "2026-07-16T09:00:00Z",
  idleExpiresAt: "2026-07-16T09:30:00Z", absoluteExpiresAt: "2026-07-16T17:00:00Z",
};

describe("session boundary policy", () => {
  it("keeps the session active immediately before idle expiry", () => {
    expect(evaluateSession(base, new Date("2026-07-16T09:29:59.999Z")).status).toBe("active");
  });
  it.each(["2026-07-16T09:30:00Z", "2026-07-16T09:30:00.001Z"])("expires at/after idle boundary %s", (now) => {
    expect(evaluateSession(base, new Date(now))).toEqual({ status: "expired", clearCookie: true });
  });
  it("expires at the absolute boundary even when idle is later", () => {
    expect(evaluateSession({ ...base, idleExpiresAt: "2026-07-16T18:00:00Z" }, new Date("2026-07-16T17:00:00Z"))).toEqual({ status: "expired", clearCookie: true });
  });
  it("distinguishes missing and revoked authoritative outcomes", () => {
    expect(evaluateSession(null)).toEqual({ status: "missing", clearCookie: true });
    expect(evaluateSession({ ...base, revokedAt: "2026-07-16T09:10:00Z" })).toEqual({ status: "revoked", clearCookie: true });
  });
});
