const ALLOWED_FIELDS: ReadonlySet<string> = new Set([
  "timestamp",
  "environment",
  "service_name",
  "service_version",
  "image_digest",
  "trace_id",
  "route_class",
  "duration_ms",
  "outcome",
  "dependency_outcome",
  "readiness",
  "replica_count",
  "restart_count",
  "hpa_at_max",
  "event",
  "code",
  "retryable",
  "catalog_version",
  "lab_count",
]);

const SAFE_TEXT = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/;

export type SafeTelemetryValue = string | number | boolean | null;

export function safeTelemetry(fields: Record<string, SafeTelemetryValue>): Record<string, SafeTelemetryValue> {
  for (const [key, value] of Object.entries(fields)) {
    if (!ALLOWED_FIELDS.has(key)) throw new Error(`Unsafe telemetry field: ${key}`);
    if (typeof value === "string" && !SAFE_TEXT.test(value)) throw new Error(`Unsafe telemetry value: ${key}`);
  }
  return Object.freeze({ ...fields });
}
