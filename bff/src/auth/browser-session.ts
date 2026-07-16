import type { FastifyReply, FastifyRequest } from "fastify";

export const SESSION_COOKIE = "__Host-learning_session";

export function setSessionCookie(reply: FastifyReply, opaqueSessionId: string): void {
  reply.setCookie(SESSION_COOKIE, opaqueSessionId, { path: "/", secure: true, httpOnly: true, sameSite: "lax" });
}

export function clearSessionCookie(reply: FastifyReply): void {
  reply.clearCookie(SESSION_COOKIE, { path: "/", secure: true, httpOnly: true, sameSite: "lax" });
}

export function requireExactOrigin(request: FastifyRequest, publicOrigin: string): void {
  if (request.headers.origin !== publicOrigin) throw Object.assign(new Error("ORIGIN_MISMATCH"), { statusCode: 403 });
}

export function requireCsrf(request: FastifyRequest, expected: string): void {
  const supplied = request.headers["x-csrf-token"];
  if (typeof supplied !== "string" || supplied !== expected) throw Object.assign(new Error("CSRF_INVALID"), { statusCode: 403 });
}
