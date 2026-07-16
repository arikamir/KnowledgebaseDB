import type { FastifyPluginAsync } from "fastify";
import { CORE_CONTRACT_DIGEST } from "../contracts/core-api.js";
import {
  guidanceCatalogCompatible,
  toBrowserGuidanceProblem,
  toBrowserGuidanceResult,
  toCoreGuidanceRequest,
  type BrowserGuidanceRequest,
} from "../contracts/guidance.js";
import { GUIDANCE_CATALOG_VERSION } from "../contracts/supported-guidance-topics.js";
import { generatedRouteSchema } from "../plugins/generated-validation.js";
import { registerFoundationRoute } from "./registry.js";

export interface GuidanceRouteServices {
  core: (path: string, init: RequestInit) => Promise<Response>;
}

export const guidanceRoutes: FastifyPluginAsync = async (app) => {
  const services = () => (app as unknown as { guidanceServices: GuidanceRouteServices }).guidanceServices;
  app.post<{ Body: BrowserGuidanceRequest }>(
    "/bff/v1/guidance",
    { schema: generatedRouteSchema("createBrowserGuidance") },
    async (request, reply) => {
      const startedAt = performance.now();
      const suppliedCatalog = request.headers["x-guidance-catalog-version"] as string | undefined;
      if (!guidanceCatalogCompatible(suppliedCatalog)) {
        request.log.info({ operation: "createBrowserGuidance", outcome: "catalog_mismatch", catalogVersion: suppliedCatalog }, "guidance request rejected");
        return reply.code(409).send({
          type: "about:blank", title: "Guidance catalog version is unsupported", status: 409,
          code: "CONTRACT_VERSION_UNSUPPORTED", retryable: false, fieldErrors: [], traceId: request.id,
        });
      }
      let response: Response;
      try {
        response = await services().core("/api/v1/guidance", {
          method: "POST",
          body: JSON.stringify(toCoreGuidanceRequest(request.body)),
          headers: {
            "Content-Type": "application/json",
            "X-BFF-Contract-Version": "1.0.0",
            "X-Core-Contract-Digest": CORE_CONTRACT_DIGEST,
            "X-Guidance-Catalog-Version": GUIDANCE_CATALOG_VERSION,
            "Idempotency-Key": String(request.headers["idempotency-key"] ?? ""),
          },
        });
      } catch {
        request.log.error({ operation: "createBrowserGuidance", outcome: "core_unavailable" }, "guidance dependency failed");
        return reply.code(503).send({ type: "about:blank", title: "Core is unavailable", status: 503, code: "CORE_UNAVAILABLE", retryable: true, fieldErrors: [], traceId: request.id });
      }
      const body = await response.json() as Record<string, unknown>;
      request.log.info({
        operation: "createBrowserGuidance", outcome: response.ok ? "success" : "failure",
        statusCode: response.status, catalogVersion: GUIDANCE_CATALOG_VERSION,
        costStatuses: response.ok && Array.isArray(body.lab_references) ? body.lab_references.map((item) => (item as { cost_status?: string }).cost_status) : [],
        durationMs: Math.round(performance.now() - startedAt),
      }, "guidance request completed");
      return reply.code(response.status).send(response.ok ? toBrowserGuidanceResult(body) : toBrowserGuidanceProblem(body));
    },
  );
};

registerFoundationRoute(guidanceRoutes);
