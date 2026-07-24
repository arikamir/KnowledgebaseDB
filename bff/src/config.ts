export interface BffConfig {
  host: string;
  port: number;
  coreBaseUrl: string;
  redisUrl: string;
  publicOrigin: string;
  sessionCookieName: string;
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): BffConfig {
  return {
    host: env.BFF_HOST ?? "0.0.0.0",
    port: Number(env.BFF_PORT ?? 3000),
    coreBaseUrl: env.CORE_BASE_URL ?? "http://core:8000/api/v1",
    redisUrl: env.REDIS_URL ?? "redis://redis:6379/0",
    publicOrigin: env.PUBLIC_ORIGIN ?? "http://localhost:5173",
    sessionCookieName: "__Host-learning_session",
  };
}
