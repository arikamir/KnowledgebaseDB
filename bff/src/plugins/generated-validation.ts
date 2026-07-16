import type { FastifyInstance } from "fastify";
import { BFF_OPERATIONS } from "../contracts/bff-api.js";

export function assertGeneratedRouteRegistration(app: FastifyInstance): void {
  const registered = app.printRoutes({ commonPrefix: false });
  for (const operation of BFF_OPERATIONS) {
    if (registered.includes(operation.path)) continue;
    // Story routes are registered only when their story task is active.
    if (["getBffCapabilities", "getBrowserSession", "beginLogin", "completeLogin", "logout"].includes(operation.operationId)) {
      throw new Error(`Missing foundation route: ${operation.operationId}`);
    }
  }
}
