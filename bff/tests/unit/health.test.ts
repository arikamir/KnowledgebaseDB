import { afterEach, describe, expect, it } from "vitest";
import { buildApp } from "../../src/app.js";
import { loadConfig } from "../../src/config.js";

const apps: ReturnType<typeof buildApp>[] = [];

afterEach(async () => {
  await Promise.all(apps.splice(0).map((app) => app.close()));
});

describe("health endpoints", () => {
  it("reports process liveness", async () => {
    const app = buildApp(loadConfig({}));
    apps.push(app);
    const response = await app.inject({ method: "GET", url: "/health/live" });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({ status: "ok" });
  });

  it.each(["redis", "tenant-jwks", "session-key", "bff-client-certificate", "core-tls"])(
    "removes only a replica with failed %s readiness while liveness remains up",
    async (failed) => {
      const dependencies = ["redis", "tenant-jwks", "session-key", "bff-client-certificate", "core-tls"];
      const prior = process.env.READINESS_REQUIRED_DEPENDENCIES;
      process.env.READINESS_REQUIRED_DEPENDENCIES = dependencies.join(",");
      try {
        const app = buildApp(loadConfig({}));
        apps.push(app);
        Object.assign(app, {
          readinessChecks: Object.fromEntries(dependencies.map((name) => [name, async () => name !== failed])),
        });
        const ready = await app.inject({ method: "GET", url: "/health/ready" });
        expect(ready.statusCode).toBe(503);
        expect(ready.json()).toEqual({ status: "unready", failedDependencies: [failed] });
        expect((await app.inject({ method: "GET", url: "/health/live" })).statusCode).toBe(200);
      } finally {
        if (prior === undefined) delete process.env.READINESS_REQUIRED_DEPENDENCIES;
        else process.env.READINESS_REQUIRED_DEPENDENCIES = prior;
      }
    },
  );
});
