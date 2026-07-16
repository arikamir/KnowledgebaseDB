import type { CapabilityMetadata } from "../contracts/bff-api";

export type CompatibilityCode =
  | "CONTRACT_VERSION_UNSUPPORTED"
  | "CAPABILITY_METADATA_INVALID"
  | "CAPABILITY_METADATA_UNAVAILABLE";

export class CompatibilityError extends Error {
  constructor(readonly code: CompatibilityCode) {
    super(code);
  }
}

interface CachedCapabilities {
  value: CapabilityMetadata;
  fetchedAt: number;
}

export class CapabilityPolicy {
  #cached?: CachedCapabilities;
  #refresh?: Promise<CapabilityMetadata>;

  constructor(
    private readonly fetchCapabilities: () => Promise<CapabilityMetadata>,
    private readonly now: () => number = Date.now,
  ) {}

  async forMutation(): Promise<CapabilityMetadata> {
    const cached = await this.#fresh(60_000);
    if (cached.status !== "compatible") throw new CompatibilityError("CONTRACT_VERSION_UNSUPPORTED");
    return cached;
  }

  async forRead(): Promise<CapabilityMetadata> {
    try {
      return await this.#fresh(45_000);
    } catch (error) {
      if (this.#cached && this.now() - this.#cached.fetchedAt <= 300_000) return this.#cached.value;
      throw error;
    }
  }

  clear(): void {
    this.#cached = undefined;
    this.#refresh = undefined;
  }

  async #fresh(maxAgeMs: number): Promise<CapabilityMetadata> {
    if (this.#cached && this.now() - this.#cached.fetchedAt <= maxAgeMs) return this.#cached.value;
    if (!this.#refresh) {
      this.#refresh = this.fetchCapabilities()
        .then((value) => {
          if (!value || !Array.isArray(value.supportedContractVersions) || !value.generatedAt) {
            throw new CompatibilityError("CAPABILITY_METADATA_INVALID");
          }
          this.#cached = { value, fetchedAt: this.now() };
          return value;
        })
        .catch((error: unknown) => {
          if (error instanceof CompatibilityError) throw error;
          throw new CompatibilityError("CAPABILITY_METADATA_UNAVAILABLE");
        })
        .finally(() => { this.#refresh = undefined; });
    }
    return this.#refresh;
  }
}
