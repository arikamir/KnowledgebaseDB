const PROHIBITED_KEY = /(name|email|token|cookie|authorization|profile|request|answer|objective|constraint)/i;

export type SafeTelemetryValue = string | number | boolean | null;

export function safeTelemetry(fields: Record<string, SafeTelemetryValue>): Record<string, SafeTelemetryValue> {
  for (const [key, value] of Object.entries(fields)) {
    if (PROHIBITED_KEY.test(key)) throw new Error(`Unsafe telemetry field: ${key}`);
    if (typeof value === "string" && value.length > 128) throw new Error(`Telemetry value too long: ${key}`);
  }
  return Object.freeze({ ...fields });
}
