import Fastify from "fastify";
import helmet from "@fastify/helmet";
import cookie from "@fastify/cookie";
import type { BffConfig } from "./config.js";
import { healthRoutes } from "./routes/health.js";
import { capabilityRoutes } from "./routes/capabilities.js";
import { authRoutes } from "./routes/auth.js";
import { internalLifecycleRoutes } from "./routes/internal-lifecycle.js";

export function buildApp(config: BffConfig) {
  const app = Fastify({ logger: true, trustProxy: true });
  Object.assign(app, { config });
  void app.register(helmet, { contentSecurityPolicy: false });
  void app.register(cookie);
  void app.register(healthRoutes);
  void app.register(capabilityRoutes);
  void app.register(authRoutes);
  void app.register(internalLifecycleRoutes);
  return app;
}
