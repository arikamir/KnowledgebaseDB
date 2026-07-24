export type CertificateStatus = "active" | "candidate" | "retained" | "quarantined" | "retired" | "revoked";

export interface RotationEvidence {
  at: string;
  event: string;
  version: string;
  replicaId?: string;
  reason?: string;
}

interface VersionState {
  version: string;
  status: CertificateStatus;
  introducedAt: number;
  activatedAt?: number;
  releaseRequired?: boolean;
}

interface ReplicaState { version: string; ready: boolean; tokenAcquisitionSucceeded: boolean }

export class CertificateRotationCoordinator {
  private readonly versions = new Map<string, VersionState>();
  private readonly replicas = new Map<string, ReplicaState>();
  private readonly evidenceLog: RotationEvidence[] = [];
  private activeVersion: string;
  private candidateVersion?: string;

  constructor(activeVersion: string, now: number, private readonly clearCredentialCaches: (version: string) => void = () => undefined) {
    this.activeVersion = activeVersion;
    this.versions.set(activeVersion, { version: activeVersion, status: "active", introducedAt: now, activatedAt: now });
  }

  beginCandidate(version: string, now: number): void {
    if (this.candidateVersion || this.versions.has(version)) throw new Error("CERTIFICATE_ROTATION_ALREADY_EXISTS");
    this.candidateVersion = version;
    this.versions.set(version, { version, status: "candidate", introducedAt: now });
    this.record(now, "candidate_introduced", version);
  }

  observeReplica(replicaId: string, version: string, tokenAcquisitionSucceeded: boolean, now: number): void {
    const expected = this.candidateVersion ?? this.activeVersion;
    const ready = version === expected && tokenAcquisitionSucceeded && this.versions.get(version)?.status !== "revoked";
    this.replicas.set(replicaId, { version, ready, tokenAcquisitionSucceeded });
    this.record(now, ready ? "replica_converged" : "replica_removed_from_service", version, replicaId);
    if (version === this.candidateVersion && !tokenAcquisitionSucceeded) this.quarantineCandidate("TOKEN_ACQUISITION_FAILED", now);
  }

  activateCandidate(now: number): void {
    const candidate = this.requireCandidate();
    if (candidate.status === "quarantined") throw new Error("CANDIDATE_OPERATOR_RELEASE_REQUIRED");
    if (!this.allReplicasConverged(candidate.version)) throw new Error("CERTIFICATE_REPLICA_CONVERGENCE_REQUIRED");
    this.versions.get(this.activeVersion)!.status = "retained";
    candidate.status = "active"; candidate.activatedAt = now;
    this.activeVersion = candidate.version;
    this.candidateVersion = undefined;
    this.record(now, "candidate_activated", candidate.version);
  }

  retirePrevious(version: string, now: number): void {
    const previous = this.versions.get(version);
    const active = this.versions.get(this.activeVersion)!;
    if (!previous || previous.status !== "retained" || !active.activatedAt) throw new Error("RETAINED_CERTIFICATE_REQUIRED");
    if (now - active.activatedAt < 24 * 60 * 60 * 1000) throw new Error("CERTIFICATE_OVERLAP_TOO_SHORT");
    if (!this.allReplicasConverged(this.activeVersion)) throw new Error("CERTIFICATE_REPLICA_CONVERGENCE_REQUIRED");
    previous.status = "retired";
    this.record(now, now - active.activatedAt > 48 * 60 * 60 * 1000 ? "retired_late_page_required" : "retired", version);
  }

  quarantineCandidate(reason: string, now: number): void {
    const candidate = this.requireCandidate();
    candidate.status = "quarantined"; candidate.releaseRequired = true;
    this.record(now, "candidate_quarantined_page_required", candidate.version, undefined, reason);
  }

  operatorRelease(now: number): void {
    const candidate = this.requireCandidate();
    if (candidate.status !== "quarantined" || !candidate.releaseRequired) throw new Error("QUARANTINED_CANDIDATE_REQUIRED");
    candidate.status = "candidate"; candidate.releaseRequired = false;
    this.record(now, "candidate_operator_released", candidate.version);
  }

  enforceConvergenceDeadline(now: number): void {
    const candidate = this.requireCandidate();
    if (!this.allReplicasConverged(candidate.version) && now - candidate.introducedAt >= 24 * 60 * 60 * 1000) {
      this.quarantineCandidate("REPLICA_CONVERGENCE_TIMEOUT", now);
    }
  }

  rollbackCandidate(now: number): void {
    const candidate = this.requireCandidate();
    candidate.status = "quarantined"; candidate.releaseRequired = true;
    for (const replica of this.replicas.values()) replica.ready = replica.version === this.activeVersion && replica.tokenAcquisitionSucceeded;
    this.record(now, "candidate_rolled_back", candidate.version);
  }

  emergencyRevoke(version: string, now: number): void {
    const state = this.versions.get(version);
    if (!state || state.status === "retired") throw new Error("CERTIFICATE_VERSION_NOT_ACTIVE");
    state.status = "revoked";
    this.clearCredentialCaches(version);
    for (const replica of this.replicas.values()) if (replica.version === version) replica.ready = false;
    if (this.candidateVersion === version) this.candidateVersion = undefined;
    this.record(now, "certificate_emergency_revoked_no_fallback", version);
  }

  isReplicaReady(replicaId: string): boolean { return this.replicas.get(replicaId)?.ready ?? false; }
  status(version: string): CertificateStatus | undefined { return this.versions.get(version)?.status; }
  evidence(): readonly RotationEvidence[] { return this.evidenceLog; }

  private requireCandidate(): VersionState {
    const candidate = this.candidateVersion ? this.versions.get(this.candidateVersion) : undefined;
    if (!candidate) throw new Error("CERTIFICATE_CANDIDATE_REQUIRED");
    return candidate;
  }
  private allReplicasConverged(version: string): boolean {
    return this.replicas.size > 0 && [...this.replicas.values()].every((replica) => replica.version === version && replica.ready);
  }
  private record(at: number, event: string, version: string, replicaId?: string, reason?: string): void {
    this.evidenceLog.push({ at: new Date(at).toISOString(), event, version, ...(replicaId ? { replicaId } : {}), ...(reason ? { reason } : {}) });
  }
}
