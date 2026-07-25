import type { FastifyPluginAsync, FastifyReply, FastifyRequest } from "fastify";
import { CORE_CONTRACT_DIGEST } from "../contracts/core-api.js";
import {
  toBrowserProgressProblem,
  toBrowserProgressReview,
  toCoreProgressCheckIn,
  type BrowserProgressCheckInRequest,
} from "../contracts/progress.js";
import { generatedRouteSchema } from "../plugins/generated-validation.js";
import { registerFoundationRoute } from "./registry.js";

export interface ProgressRouteServices {
  core: (path: string, init: RequestInit) => Promise<Response>;
}

interface ValidationIssue {
  instancePath?: string;
  message?: string;
  params?: { missingProperty?: string };
}

function browserFieldName(value: string): string {
  return value
    .replace(/^\//, "")
    .replace(/[-_]([a-z])/g, (_match, letter: string) => letter.toUpperCase())
    || "request";
}

function coreHeaders(request: FastifyRequest, json = false): Record<string, string> {
  const headers: Record<string, string> = {
    "X-BFF-Contract-Version": "1.0.0",
    "X-Core-Contract-Digest": CORE_CONTRACT_DIGEST,
    "X-Correlation-ID": request.id,
  };
  if (json) headers["Content-Type"] = "application/json";
  const idempotencyKey = request.headers["idempotency-key"];
  if (typeof idempotencyKey === "string") headers["Idempotency-Key"] = idempotencyKey;
  return headers;
}

async function relay(
  request: FastifyRequest,
  reply: FastifyReply,
  core: ProgressRouteServices["core"],
  path: string,
  init: RequestInit,
  routeClass: "progress_mutation" | "progress_review",
): Promise<unknown> {
  const startedAt = performance.now();
  try {
    const response = await core(path, init);
    const body = await response.json() as Record<string, unknown>;
    request.server.log.info({
      traceId: request.id,
      routeClass,
      durationMs: Math.round(performance.now() - startedAt),
      outcome: response.ok ? "success" : "denied",
      dependencyOutcome: "core_available",
      statusCode: response.status,
      denialCode: response.ok || typeof body.code !== "string" ? undefined : body.code,
    }, "progress request completed");
    return reply
      .code(response.status)
      .send(response.ok ? toBrowserProgressReview(body) : toBrowserProgressProblem(body));
  } catch {
    request.server.log.error({
      traceId: request.id,
      routeClass,
      durationMs: Math.round(performance.now() - startedAt),
      outcome: "dependency_unavailable",
      dependencyOutcome: "core_unavailable",
      statusCode: 503,
      denialCode: "CORE_UNAVAILABLE",
    }, "progress dependency failed");
    return reply.code(503).send({
      type: "about:blank",
      title: "Core is unavailable",
      status: 503,
      code: "CORE_UNAVAILABLE",
      detail: null,
      traceId: request.id,
      retryable: true,
      fieldErrors: [],
    });
  }
}

export const progressRoutes: FastifyPluginAsync = async (app) => {
  const services = () =>
    (app as unknown as { progressServices?: ProgressRouteServices }).progressServices;

  app.setErrorHandler((error, request, reply) => {
    const issues = (error as typeof error & { validation?: ValidationIssue[] }).validation;
    if (!issues) return reply.send(error);
    const grouped = new Map<string, string[]>();
    for (const issue of issues) {
      const field = browserFieldName(
        issue.params?.missingProperty ?? issue.instancePath ?? "request",
      );
      grouped.set(field, [...(grouped.get(field) ?? []), issue.message ?? "Invalid value"]);
    }
    request.server.log.info({
      traceId: request.id,
      routeClass: request.method === "POST" ? "progress_mutation" : "progress_review",
      durationMs: 0,
      outcome: "denied",
      dependencyOutcome: "not_called",
      statusCode: 422,
      denialCode: "VALIDATION_FAILED",
    }, "progress request denied");
    return reply.code(422).type("application/problem+json").send({
      type: "https://knowledgebasedb.invalid/problems/validation-failed",
      title: "Request validation failed",
      status: 422,
      code: "VALIDATION_FAILED",
      detail: null,
      traceId: request.id,
      retryable: false,
      fieldErrors: [...grouped.entries()].map(([field, messages]) => ({ field, messages })),
    });
  });

  app.post<{ Body: BrowserProgressCheckInRequest }>(
    "/bff/v1/progress/check-ins",
    { schema: generatedRouteSchema("createBrowserProgressCheckIn"), logLevel: "silent" },
    (request, reply) => relay(
      request,
      reply,
      services()?.core ?? (() => Promise.reject(new Error("CORE_SERVICE_NOT_CONFIGURED"))),
      "/api/v1/progress/check-ins",
      {
        method: "POST",
        headers: coreHeaders(request, true),
        body: JSON.stringify(toCoreProgressCheckIn(request.body)),
      },
      "progress_mutation",
    ),
  );

  app.get<{ Querystring: { roadmapId: string } }>(
    "/bff/v1/progress/reviews",
    { schema: generatedRouteSchema("getBrowserProgressReview"), logLevel: "silent" },
    (request, reply) => relay(
      request,
      reply,
      services()?.core ?? (() => Promise.reject(new Error("CORE_SERVICE_NOT_CONFIGURED"))),
      `/api/v1/progress/reviews?roadmap_id=${encodeURIComponent(request.query.roadmapId)}`,
      { method: "GET", headers: coreHeaders(request) },
      "progress_review",
    ),
  );
};

registerFoundationRoute(progressRoutes);
