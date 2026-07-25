/* eslint-disable @typescript-eslint/no-explicit-any -- Fastify generated-schema boundary handlers */
import type { FastifyPluginAsync } from "fastify";
import { CORE_CONTRACT_DIGEST } from "../contracts/core-api.js";
import { toBrowserLearningSession, toBrowserProblem, toBrowserReviewAttempt, toBrowserReviewFeedback, toBrowserReviewResult, toCoreLabReport, toCoreReviewAnswer } from "../contracts/learning.js";
import { generatedRouteSchema } from "../plugins/generated-validation.js";
import { registerFoundationRoute } from "./registry.js";

interface LearningServices { core: (path: string, init: RequestInit) => Promise<Response>; }
const headers = (request: any, json = false) => ({ ...(json ? { "Content-Type": "application/json" } : {}), "X-BFF-Contract-Version": "1.0.0", "X-Core-Contract-Digest": CORE_CONTRACT_DIGEST, ...(request.headers["idempotency-key"] ? { "Idempotency-Key": String(request.headers["idempotency-key"]) } : {}) });

export const learningRoutes: FastifyPluginAsync = async (app) => {
  const core = () => (app as unknown as { learningServices?: LearningServices }).learningServices?.core;
  const relay = async (request: any, reply: any, path: string, init: RequestInit, map: (value: any) => any) => {
    const startedAt = performance.now();
    const operation = request.routeOptions.url;
    try { const service = core(); if (!service) throw new Error("CORE_SERVICE_NOT_CONFIGURED"); const response = await service(path, init); const body = response.status === 204 ? {} : await response.json(); request.log.info({ operation, outcome: response.ok ? "success" : "failure", statusCode: response.status, durationMs: Math.round(performance.now() - startedAt) }, "learning request completed"); return reply.code(response.status).send(response.ok ? map(body) : toBrowserProblem(body)); }
    catch { request.log.error({ operation, outcome: "core_unavailable", durationMs: Math.round(performance.now() - startedAt) }, "learning dependency failed"); return reply.code(503).send({ type: "about:blank", title: "Core is unavailable", status: 503, code: "CORE_UNAVAILABLE", traceId: request.id, retryable: true, fieldErrors: [] }); }
  };
  app.get("/bff/v1/learning-sessions", { schema: generatedRouteSchema("listBrowserLearningSessions") }, (req: any, rep) => relay(req, rep, `/api/v1/learning-sessions?roadmap_id=${encodeURIComponent(req.query.roadmapId)}`, { headers: headers(req) }, (items) => items.map(toBrowserLearningSession)));
  app.get("/bff/v1/learning-sessions/:id", { schema: generatedRouteSchema("getBrowserLearningSession") }, (req: any, rep) => relay(req, rep, `/api/v1/learning-sessions/${encodeURIComponent(req.params.id)}`, { headers: headers(req) }, toBrowserLearningSession));
  app.post("/bff/v1/learning-sessions/:id/start", { schema: generatedRouteSchema("startBrowserLearningSession") }, (req: any, rep) => relay(req, rep, `/api/v1/learning-sessions/${encodeURIComponent(req.params.id)}/start`, { method: "POST", headers: headers(req) }, toBrowserLearningSession));
  app.put("/bff/v1/learning-sessions/:id/steps/:stepId/completion", { schema: generatedRouteSchema("completeBrowserLearningStep") }, (req: any, rep) => relay(req, rep, `/api/v1/learning-sessions/${encodeURIComponent(req.params.id)}/steps/${encodeURIComponent(req.params.stepId)}/completion`, { method: "PUT", headers: headers(req) }, toBrowserLearningSession));
  app.get("/bff/v1/learning-sessions/:id/review-attempts", { schema: generatedRouteSchema("listBrowserReviewAttempts") }, (req: any, rep) => relay(req, rep, `/api/v1/learning-sessions/${encodeURIComponent(req.params.id)}/review-attempts`, { headers: headers(req) }, (items) => items.map(toBrowserReviewAttempt)));
  app.post("/bff/v1/learning-sessions/:id/review-attempts", { schema: generatedRouteSchema("createBrowserReviewAttempt") }, (req: any, rep) => relay(req, rep, `/api/v1/learning-sessions/${encodeURIComponent(req.params.id)}/review-attempts`, { method: "POST", headers: headers(req) }, toBrowserReviewAttempt));
  app.get("/bff/v1/review-attempts/:id", { schema: generatedRouteSchema("getBrowserReviewAttempt") }, (req: any, rep) => relay(req, rep, `/api/v1/review-attempts/${encodeURIComponent(req.params.id)}`, { headers: headers(req) }, toBrowserReviewAttempt));
  app.put("/bff/v1/review-attempts/:id/answers/:questionId", { schema: generatedRouteSchema("answerBrowserReviewQuestion") }, (req: any, rep) => relay(req, rep, `/api/v1/review-attempts/${encodeURIComponent(req.params.id)}/answers/${encodeURIComponent(req.params.questionId)}`, { method: "PUT", headers: headers(req, true), body: JSON.stringify(toCoreReviewAnswer(req.body)) }, toBrowserReviewFeedback));
  app.post("/bff/v1/review-attempts/:id/submit", { schema: generatedRouteSchema("submitBrowserReviewAttempt") }, (req: any, rep) => relay(req, rep, `/api/v1/review-attempts/${encodeURIComponent(req.params.id)}/submit`, { method: "POST", headers: headers(req) }, toBrowserReviewResult));
  app.post("/bff/v1/lab-references/:id/reports", { schema: generatedRouteSchema("reportBrowserLabReference") }, (req: any, rep) => relay(req, rep, `/api/v1/lab-references/${encodeURIComponent(req.params.id)}/reports`, { method: "POST", headers: headers(req, true), body: JSON.stringify(toCoreLabReport(req.body)) }, (value) => value));
  app.get("/bff/v1/learning/next-action", { schema: generatedRouteSchema("getBrowserNextLearningAction") }, (req: any, rep) => relay(req, rep, `/api/v1/learning/next-action?roadmap_id=${encodeURIComponent(req.query.roadmapId)}`, { headers: headers(req) }, (value) => value));
};

registerFoundationRoute(learningRoutes);
