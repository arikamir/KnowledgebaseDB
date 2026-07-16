import type { FastifyPluginAsync } from "fastify";

export const healthRoutes: FastifyPluginAsync = async (app) => {
  app.get("/health/live", async () => ({ status: "ok" }));
  app.get("/health/ready", async (_request, reply) => {
    const checks = (app as unknown as { readinessChecks?: Record<string, () => Promise<boolean>> }).readinessChecks ?? {};
    const failed: string[] = [];
    for (const [name, check] of Object.entries(checks)) {
      try { if (!await check()) failed.push(name); } catch { failed.push(name); }
    }
    if (failed.length) return reply.code(503).send({ status: "unready", failedDependencies: failed });
    return { status: "ready" };
  });
};
