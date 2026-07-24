import type { FastifyPluginAsync } from "fastify";
import { randomBytes } from "node:crypto";
import { createAuthorizationRequest } from "../auth/entra.js";
import { approveSessionActivation, type LifecycleClient } from "../auth/lifecycle-gate.js";
import { clearSessionCookie, requireCsrf, requireExactOrigin, SESSION_COOKIE, setSessionCookie } from "../auth/browser-session.js";
import { evaluateSession, touchSession } from "../sessions/session-policy.js";
import { SessionDependencyUnavailable, type EncryptedSessionStore, type SessionData } from "../sessions/session-store.js";
import { generatedRouteSchema } from "../plugins/generated-validation.js";

export interface AuthRouteServices {
  sessions: EncryptedSessionStore;
  lifecycle: LifecycleClient;
  publicOrigin: string;
  authorizationUrl: string;
  exchangeCode: (code: string, state: string) => Promise<{ tenantId: string; objectId: string }>;
}

export const authRoutes: FastifyPluginAsync = async (app) => {
  const services = () => (app as unknown as { authServices: AuthRouteServices }).authServices;

  app.get<{ Querystring: { return_to?: string } }>("/bff/v1/auth/login", { schema: generatedRouteSchema("beginLogin") }, async (request, reply) => {
    const authorization = createAuthorizationRequest(request.query.return_to);
    reply.setCookie("__Host-learning_auth_state", Buffer.from(JSON.stringify(authorization)).toString("base64url"), { path: "/bff/v1/auth/callback", secure: true, httpOnly: true, sameSite: "lax" });
    return reply.redirect(`${services().authorizationUrl}?state=${encodeURIComponent(authorization.state)}&nonce=${encodeURIComponent(authorization.nonce)}&code_challenge=${encodeURIComponent(authorization.codeChallenge)}`, 302);
  });

  app.get<{ Querystring: { code: string; state: string } }>("/bff/v1/auth/callback", { schema: generatedRouteSchema("completeLogin") }, async (request, reply) => {
    const token = await services().exchangeCode(request.query.code, request.query.state);
    const employeeId = await approveSessionActivation(services().lifecycle, token.tenantId, token.objectId);
    const now = new Date();
    const session: SessionData = {
      sessionId: randomBytes(32).toString("base64url"), ownerKey: `${token.tenantId}:${token.objectId}`,
      csrfToken: randomBytes(24).toString("base64url"), issuedAt: now.toISOString(), lastSeenAt: now.toISOString(),
      idleExpiresAt: new Date(now.getTime() + 30 * 60_000).toISOString(), absoluteExpiresAt: new Date(now.getTime() + 8 * 60 * 60_000).toISOString(),
    };
    await services().sessions.save(session);
    setSessionCookie(reply, session.sessionId);
    return reply.redirect(`/roadmaps?employee=${encodeURIComponent(employeeId)}`, 303);
  });

  app.get("/bff/v1/session", { schema: generatedRouteSchema("getBrowserSession") }, async (request, reply) => {
    const sessionId = request.cookies[SESSION_COOKIE];
    if (!sessionId) return { authenticated: false };
    try {
      const session = await services().sessions.load(sessionId);
      const outcome = evaluateSession(session);
      if (outcome.status !== "active") { clearSessionCookie(reply); return { authenticated: false }; }
      const active = outcome.shouldTouch ? touchSession(outcome.session) : outcome.session;
      if (outcome.shouldTouch) await services().sessions.save(active);
      return { authenticated: true, csrfToken: active.csrfToken, idleExpiresAt: active.idleExpiresAt, absoluteExpiresAt: active.absoluteExpiresAt };
    } catch (error) {
      if (error instanceof SessionDependencyUnavailable) return reply.code(503).send({ code: error.code });
      throw error;
    }
  });

  app.post("/bff/v1/auth/logout", { schema: generatedRouteSchema("logout") }, async (request, reply) => {
    requireExactOrigin(request, services().publicOrigin);
    const sessionId = request.cookies[SESSION_COOKIE];
    if (sessionId) {
      try {
        const session = await services().sessions.load(sessionId);
        if (session) requireCsrf(request, session.csrfToken);
        await services().sessions.revoke(sessionId);
      } catch (error) {
        if (error instanceof SessionDependencyUnavailable) return reply.code(503).send({ code: error.code });
        throw error;
      }
    }
    clearSessionCookie(reply);
    return reply.redirect("/", 303);
  });
};
