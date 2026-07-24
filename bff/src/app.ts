import Fastify from "fastify";
import helmet from "@fastify/helmet";
import cookie from "@fastify/cookie";
import type { BffConfig } from "./config.js";
import { healthRoutes } from "./routes/health.js";
import { capabilityRoutes } from "./routes/capabilities.js";
import { authRoutes } from "./routes/auth.js";
import { internalLifecycleRoutes } from "./routes/internal-lifecycle.js";
import { installGeneratedSchemas } from "./plugins/generated-validation.js";
import { installFoundationRoutes } from "./routes/registry.js";
import "./routes/roadmaps.js";
import "./routes/guidance.js";
import "./routes/learning.js";
import "./routes/progress.js";

export function buildApp(config: BffConfig) {
  const app = Fastify({ logger: true, trustProxy: true });
  Object.assign(app, { config });
  installGeneratedSchemas(app);
  void app.register(helmet, {
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'none'"],
        baseUri: ["'none'"],
        frameAncestors: ["'none'"],
        formAction: ["'self'"],
      },
    },
    referrerPolicy: { policy: "no-referrer" },
  });
  void app.register(cookie);
  void app.register(healthRoutes);
  void app.register(capabilityRoutes);
  void app.register(authRoutes);
  void app.register(internalLifecycleRoutes);
  void installFoundationRoutes(app);
  return app;
}
