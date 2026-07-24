import type { FastifyInstance } from "fastify";
import { BFF_COMPONENT_SCHEMAS, BFF_OPERATIONS, BFF_ROUTE_SCHEMAS, type BffOperationId } from "../contracts/bff-api.js";

export function installGeneratedSchemas(app: FastifyInstance): void {
  for (const schema of BFF_COMPONENT_SCHEMAS) app.addSchema(schema);
}

export function generatedRouteSchema(operationId: BffOperationId): object {
  return BFF_ROUTE_SCHEMAS[operationId];
}

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
