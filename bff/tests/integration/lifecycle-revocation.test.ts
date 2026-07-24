import Fastify from "fastify";
import { afterEach, describe, expect, it } from "vitest";
import { internalLifecycleRoutes } from "../../src/routes/internal-lifecycle.js";
import { EncryptedSessionStore, type SessionData } from "../../src/sessions/session-store.js";
import { EncryptionKeyRing } from "../../src/sessions/encryption-key-ring.js";
import { MemorySessionBackend } from "../helpers/session.js";

const apps: ReturnType<typeof Fastify>[] = [];
afterEach(async () => { await Promise.all(apps.splice(0).map((app) => app.close())); });

async function appWithRole(roles: string[]) {
  const backend = new MemorySessionBackend();
  const store = new EncryptedSessionStore(backend, new EncryptionKeyRing([{ version: "v1", key: Buffer.alloc(32, 1), mode: "active" }]));
  const session: SessionData = { sessionId: "session", ownerKey: "tenant:owner", csrfToken: "csrf", issuedAt: "2026-07-17T00:00:00Z", lastSeenAt: "2026-07-17T00:00:00Z", idleExpiresAt: "2026-07-17T00:30:00Z", absoluteExpiresAt: "2026-07-17T08:00:00Z" };
  await store.save(session);
  const app = Fastify();
  apps.push(app);
  Object.assign(app, { sessionStore: store });
  app.addHook("preHandler", async (request) => { Object.assign(request, { machinePrincipal: { clientId: "lifecycle", roles } }); });
  await app.register(internalLifecycleRoutes);
  return { app, store };
}

const payload = { tenantId: "tenant", objectId: "owner", reconciliationRunId: "run-1", departedAt: "2026-07-17T00:00:00Z" };

describe("lifecycle session revocation", () => {
  it("authenticates the exact role, revokes owner sessions, and acknowledges repeats", async () => {
    const { app, store } = await appWithRole(["LearningBff.Session.Revoke"]);
    const first = await app.inject({ method: "POST", url: "/internal/v1/session-revocations", payload });
    const repeat = await app.inject({ method: "POST", url: "/internal/v1/session-revocations", payload });
    expect(first.statusCode).toBe(200);
    expect(first.json()).toMatchObject({ status: "acknowledged", reconciliationRunId: "run-1" });
    expect(repeat.statusCode).toBe(200);
    expect(repeat.json()).toMatchObject({ status: "acknowledged", reconciliationRunId: "run-1" });
    expect(await store.load("session")).toBeNull();
  });

  it.each([{ roles: [] }, { roles: ["CareerAgent.Health.Read"] }])("rejects missing or wrong application role", async ({ roles }) => {
    const { app } = await appWithRole(roles);
    const response = await app.inject({ method: "POST", url: "/internal/v1/session-revocations", payload });
    expect(response.statusCode).toBe(403);
    expect(response.json()).toEqual({ code: "MACHINE_ROLE_REQUIRED" });
  });
});
