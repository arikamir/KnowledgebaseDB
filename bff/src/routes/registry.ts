import type { FastifyInstance, FastifyPluginAsync } from "fastify";

const foundationRoutes: FastifyPluginAsync[] = [];

export function registerFoundationRoute(plugin: FastifyPluginAsync): void { foundationRoutes.push(plugin); }

export async function installFoundationRoutes(app: FastifyInstance): Promise<void> {
  for (const plugin of foundationRoutes) await app.register(plugin);
}
