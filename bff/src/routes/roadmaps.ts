import type { FastifyPluginAsync, FastifyReply } from "fastify";
import { CORE_CONTRACT_DIGEST } from "../contracts/core-api.js";
import { generatedRouteSchema } from "../plugins/generated-validation.js";
import { registerFoundationRoute } from "./registry.js";
import { toBrowserRoadmap, toBrowserRoadmapList, toBrowserRoadmapResult, toCoreRoadmapRequest, type BrowserRoadmapCreateRequest } from "../contracts/roadmap.js";

export interface RoadmapRouteServices {
  core: (path: string, init: RequestInit) => Promise<Response>;
}

export const roadmapRoutes: FastifyPluginAsync = async (app) => {
  const services = () => (app as unknown as { roadmapServices?: RoadmapRouteServices }).roadmapServices;
  const unavailable = (reply: FastifyReply, traceId: string) => reply.code(503).send({ type: "about:blank", title: "Core is unavailable", status: 503, code: "CORE_UNAVAILABLE", retryable: true, fieldErrors: [], traceId });
  app.post<{ Body: BrowserRoadmapCreateRequest }>("/bff/v1/roadmaps", { schema: generatedRouteSchema("createBrowserRoadmap") }, async (request, reply) => {
    const startedAt = performance.now();
    const service = services();
    if (!service) return unavailable(reply, request.id);
    let response: Response;
    try { response = await service.core("/api/v1/roadmaps", {
      method: "POST", body: JSON.stringify(toCoreRoadmapRequest(request.body)),
      headers: { "Content-Type": "application/json", "X-BFF-Contract-Version": "1.0.0", "X-Core-Contract-Digest": CORE_CONTRACT_DIGEST, "Idempotency-Key": String(request.headers["idempotency-key"] ?? "") },
    }); } catch { return unavailable(reply, request.id); }
    const body = await response.json() as Record<string, unknown>;
    request.log.info({ operation: "createBrowserRoadmap", outcome: response.ok ? "success" : "failure", durationMs: Math.round(performance.now() - startedAt), statusCode: response.status }, "roadmap request completed");
    return reply.code(response.status).send(response.ok ? toBrowserRoadmapResult(body) : body);
  });
  app.get("/bff/v1/roadmaps", { schema: generatedRouteSchema("listBrowserRoadmaps") }, async (request, reply) => {
    const service = services();
    if (!service) return unavailable(reply, request.id);
    let response: Response;
    try { response = await service.core("/api/v1/roadmaps", { method: "GET", headers: { "X-BFF-Contract-Version": "1.0.0" } }); } catch { return unavailable(reply, request.id); }
    const body = await response.json();
    return reply.code(response.status).send(response.ok ? toBrowserRoadmapList(body) : body);
  });
  app.get<{ Params: { id: string } }>("/bff/v1/roadmaps/:id", { schema: generatedRouteSchema("getBrowserRoadmap") }, async (request, reply) => {
    const service = services();
    if (!service) return unavailable(reply, request.id);
    let response: Response;
    try { response = await service.core(`/api/v1/roadmaps/${encodeURIComponent(request.params.id)}`, { method: "GET", headers: { "X-BFF-Contract-Version": "1.0.0" } }); } catch { return unavailable(reply, request.id); }
    const body = await response.json();
    return reply.code(response.status).send(response.ok ? toBrowserRoadmap(body) : body);
  });
};

registerFoundationRoute(roadmapRoutes);
