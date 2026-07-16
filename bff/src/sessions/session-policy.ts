import type { SessionData } from "./session-store.js";

export type SessionOutcome =
  | { status: "active"; session: SessionData; shouldTouch: boolean }
  | { status: "missing" | "expired" | "revoked"; clearCookie: true };

export function evaluateSession(session: SessionData | null, now = new Date()): SessionOutcome {
  if (!session) return { status: "missing", clearCookie: true };
  if (session.revokedAt) return { status: "revoked", clearCookie: true };
  if (now >= new Date(session.idleExpiresAt) || now >= new Date(session.absoluteExpiresAt)) return { status: "expired", clearCookie: true };
  const sinceTouch = now.getTime() - new Date(session.lastSeenAt).getTime();
  return { status: "active", session, shouldTouch: sinceTouch >= 60_000 };
}

export function touchSession(session: SessionData, now = new Date()): SessionData {
  const idle = new Date(Math.min(now.getTime() + 30 * 60_000, new Date(session.absoluteExpiresAt).getTime()));
  return { ...session, lastSeenAt: now.toISOString(), idleExpiresAt: idle.toISOString() };
}
