import type { FastifyPluginAsync } from "fastify";
import { BFF_CONTRACT_DIGEST, BFF_OPERATIONS } from "../contracts/bff-api.js";
import { GUIDANCE_CATALOG_VERSION } from "../contracts/supported-guidance-topics.js";
import { generatedRouteSchema } from "../plugins/generated-validation.js";

export const capabilityRoutes: FastifyPluginAsync = async (app) => {
  app.get("/bff/v1/capabilities", { schema: generatedRouteSchema("getBffCapabilities") }, async () => ({
    contractVersion: "1.0.0",
    contractDigest: BFF_CONTRACT_DIGEST,
    catalogVersion: GUIDANCE_CATALOG_VERSION,
    status: "compatible",
    generatedAt: new Date().toISOString(),
    supportedContractVersions: ["1.0.0"],
    supportedMutations: BFF_OPERATIONS.filter((operation) => ["POST", "PUT", "PATCH", "DELETE"].includes(operation.method)).map((operation) => operation.operationId),
  }));
};
