import { afterEach, describe, expect, it } from "vitest";
import { buildApp } from "../../src/app.js";

describe("BFF capabilities", () => {
  const app = buildApp({
    host: "127.0.0.1",
    port: 0,
    coreBaseUrl: "https://core.test/api/v1",
    redisUrl: "redis://redis.test:6379/0",
    publicOrigin: "https://career-agent.test",
    sessionCookieName: "__Host-learning_session",
  });

  afterEach(async () => app.close());

  it("returns the generated contract's compatibility shape", async () => {
    const response = await app.inject({ method: "GET", url: "/bff/v1/capabilities" });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      bffContractVersion: "1.4.0",
      bffApiSchemaVersion: "1.0.0",
      acceptedUiContractRange: ">=1.2.0 <2.0.0",
      core: {
        contractVersion: "1.3.0",
        acceptedBffContractRange: ">=1.1.0 <2.0.0",
        apiSchemaVersion: "1.0.0",
        guidanceTopicCatalogVersion: "1.0.0",
        compatible: true,
      },
      featureFlags: {},
    });
  });
});
