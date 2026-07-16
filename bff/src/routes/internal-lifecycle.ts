import type { FastifyPluginAsync } from "fastify";
import type { EncryptedSessionStore } from "../sessions/session-store.js";

export const internalLifecycleRoutes: FastifyPluginAsync = async (app) => {
  app.post<{ Body: { tenantId: string; objectId: string; reconciliationRunId: string } }>("/internal/v1/session-revocations", async (request, reply) => {
    const principal = (request as unknown as { machinePrincipal?: { clientId: string; roles: string[] } }).machinePrincipal;
    if (!principal || !principal.roles.includes("LearningBff.Session.Revoke")) return reply.code(403).send({ code: "MACHINE_ROLE_REQUIRED" });
    const store = (app as unknown as { sessionStore: EncryptedSessionStore }).sessionStore;
    const revoked = await store.revokeOwner(`${request.body.tenantId}:${request.body.objectId}`);
    return { status: "acknowledged", reconciliationRunId: request.body.reconciliationRunId, revokedSessions: revoked };
  });
};
