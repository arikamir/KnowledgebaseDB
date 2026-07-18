import type { FastifyPluginAsync } from "fastify";
import { GUIDANCE_CATALOG_VERSION } from "../contracts/supported-guidance-topics.js";
import { generatedRouteSchema } from "../plugins/generated-validation.js";

export const capabilityRoutes: FastifyPluginAsync = async (app) => {
  app.get("/bff/v1/capabilities", { schema: generatedRouteSchema("getBffCapabilities") }, async () => ({
    bffContractVersion: "1.4.0",
    bffApiSchemaVersion: "1.0.0",
    acceptedUiContractRange: ">=1.2.0 <2.0.0",
    core: {
      contractVersion: "1.3.0",
      acceptedBffContractRange: ">=1.1.0 <2.0.0",
      apiSchemaVersion: "1.0.0",
      guidanceTopicCatalogVersion: GUIDANCE_CATALOG_VERSION,
      compatible: true,
    },
    featureFlags: {},
  }));
};
