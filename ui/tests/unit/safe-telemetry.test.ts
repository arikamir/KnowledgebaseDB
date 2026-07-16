import { describe, expect, it } from "vitest";
import { safeTelemetry } from "../../src/telemetry/safe-telemetry";

describe("safeTelemetry", () => {
  it("accepts and freezes the approved non-personal envelope", () => {
    const envelope = safeTelemetry({
      event: "guidance_success",
      route_class: "guidance_mutation",
      duration_ms: 125,
      outcome: "success",
      dependency_outcome: "core_available",
      retryable: false,
    });

    expect(envelope).toEqual({
      event: "guidance_success",
      route_class: "guidance_mutation",
      duration_ms: 125,
      outcome: "success",
      dependency_outcome: "core_available",
      retryable: false,
    });
    expect(Object.isFrozen(envelope)).toBe(true);
  });

  it.each([
    "name", "email", "token", "cookie", "authorization", "profile",
    "request_body", "answer", "objective", "roadmap_id",
  ])("rejects prohibited or unregistered field %s", (field) => {
    expect(() => safeTelemetry({ [field]: "redacted" })).toThrow(`Unsafe telemetry field: ${field}`);
  });

  it.each([
    "employee@example.test",
    "Bearer secret-access-token",
    "employee input with spaces",
    "line-one\nline-two",
  ])("rejects free-form or credential-shaped text", (value) => {
    expect(() => safeTelemetry({ outcome: value })).toThrow("Unsafe telemetry value: outcome");
  });
});
