export interface RuntimeConfig {
  bffBasePath: "/bff/v1";
  environmentName: string;
  telemetryEnabled: boolean;
}

let cached: RuntimeConfig | undefined;

export async function loadRuntimeConfig(fetcher: typeof fetch = fetch): Promise<RuntimeConfig> {
  if (cached) return cached;
  const response = await fetcher("/runtime-config.json", { cache: "no-store", credentials: "same-origin" });
  if (!response.ok) throw new Error("RUNTIME_CONFIG_UNAVAILABLE");
  const value = await response.json() as Partial<RuntimeConfig>;
  if (value.bffBasePath !== "/bff/v1" || typeof value.environmentName !== "string" || typeof value.telemetryEnabled !== "boolean") {
    throw new Error("RUNTIME_CONFIG_INVALID");
  }
  cached = value as RuntimeConfig;
  return cached;
}
