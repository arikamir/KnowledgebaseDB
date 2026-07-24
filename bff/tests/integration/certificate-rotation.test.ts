import { describe, expect, it } from "vitest";
import { CertificateRotationCoordinator } from "../../src/auth/certificate-rotation.js";

const HOUR = 60 * 60 * 1000;
const NOW = Date.parse("2026-07-17T00:00:00Z");
const tokenPaths = ["fresh-callback", "existing-session-refresh", "delegated-core-token", "health-app-token"];

describe("BFF confidential-client certificate rotation", () => {
  it("converges every replica, preserves all token paths, overlaps 24 hours, and retires by 48 hours", () => {
    const coordinator = new CertificateRotationCoordinator("old", NOW);
    coordinator.beginCandidate("new", NOW);
    coordinator.observeReplica("bff-0", "new", tokenPaths.every(Boolean), NOW + HOUR);
    coordinator.observeReplica("bff-1", "new", tokenPaths.every(Boolean), NOW + HOUR);
    coordinator.activateCandidate(NOW + HOUR);
    expect(coordinator.status("old")).toBe("retained");
    expect(() => coordinator.retirePrevious("old", NOW + 24 * HOUR)).toThrow("OVERLAP_TOO_SHORT");
    coordinator.retirePrevious("old", NOW + 25 * HOUR);
    expect(coordinator.status("old")).toBe("retired");
    expect(coordinator.evidence().some((event) => event.event === "retired")).toBe(true);
  });

  it("removes a nonconverged replica, quarantines/pages at 24 hours, and requires operator release", () => {
    const coordinator = new CertificateRotationCoordinator("old", NOW);
    coordinator.beginCandidate("new", NOW);
    coordinator.observeReplica("bff-0", "new", true, NOW + HOUR);
    coordinator.observeReplica("bff-1", "old", true, NOW + HOUR);
    expect(coordinator.isReplicaReady("bff-0")).toBe(true);
    expect(coordinator.isReplicaReady("bff-1")).toBe(false);
    coordinator.enforceConvergenceDeadline(NOW + 24 * HOUR);
    expect(coordinator.status("new")).toBe("quarantined");
    expect(() => coordinator.activateCandidate(NOW + 24 * HOUR)).toThrow("OPERATOR_RELEASE_REQUIRED");
    coordinator.operatorRelease(NOW + 25 * HOUR);
    coordinator.observeReplica("bff-1", "new", true, NOW + 25 * HOUR);
    coordinator.activateCandidate(NOW + 25 * HOUR);
    expect(coordinator.status("new")).toBe("active");
  });

  it("quarantines failed token acquisition and can roll back without retiring the old credential", () => {
    const coordinator = new CertificateRotationCoordinator("old", NOW);
    coordinator.beginCandidate("bad", NOW);
    coordinator.observeReplica("bff-0", "bad", false, NOW + HOUR);
    expect(coordinator.status("bad")).toBe("quarantined");
    expect(coordinator.status("old")).toBe("active");
    coordinator.rollbackCandidate(NOW + 2 * HOUR);
    expect(coordinator.status("old")).toBe("active");
    expect(coordinator.evidence().at(-1)?.event).toBe("candidate_rolled_back");
  });

  it("emergency revocation clears affected credential caches with no fallback and preserves core records", () => {
    const cleared: string[] = [];
    const savedCoreRecord = { progress: 80, roadmap: "preserved" };
    const coordinator = new CertificateRotationCoordinator("compromised", NOW, (version) => cleared.push(version));
    coordinator.observeReplica("bff-0", "compromised", true, NOW);
    coordinator.observeReplica("bff-1", "compromised", true, NOW);
    coordinator.emergencyRevoke("compromised", NOW + HOUR);
    expect(cleared).toEqual(["compromised"]);
    expect(coordinator.status("compromised")).toBe("revoked");
    expect(coordinator.isReplicaReady("bff-0")).toBe(false);
    expect(coordinator.isReplicaReady("bff-1")).toBe(false);
    expect(savedCoreRecord).toEqual({ progress: 80, roadmap: "preserved" });
    expect(coordinator.evidence().at(-1)?.event).toBe("certificate_emergency_revoked_no_fallback");
  });
});
