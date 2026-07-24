export type CapabilityFailureCode = "CONTRACT_VERSION_UNSUPPORTED" | "CAPABILITY_METADATA_INVALID" | "CAPABILITY_METADATA_UNAVAILABLE";

export interface CoreCapabilities {
  contractVersion: string;
  supportedContractVersions: string[];
  catalogVersion: string;
  mutations: string[];
}

interface CacheEntry { value: CoreCapabilities; receivedAt: number; }

export class CoreCapabilityPolicy {
  #cache?: CacheEntry;
  #refresh?: Promise<CoreCapabilities>;
  constructor(private readonly fetchCapabilities: () => Promise<CoreCapabilities>, private readonly now: () => number = Date.now) {}

  async requireMutation(operation: string): Promise<CoreCapabilities> {
    const value = await this.#get(60_000, false);
    if (!value.mutations.includes(operation)) throw new Error("CONTRACT_VERSION_UNSUPPORTED");
    return value;
  }

  async safeRead(): Promise<CoreCapabilities> { return this.#get(45_000, true); }

  async #get(refreshAge: number, allowStale: boolean): Promise<CoreCapabilities> {
    if (this.#cache && this.now() - this.#cache.receivedAt <= refreshAge) return this.#cache.value;
    if (!this.#refresh) {
      this.#refresh = this.fetchCapabilities().then((value) => {
        if (!value.contractVersion || !Array.isArray(value.supportedContractVersions) || !Array.isArray(value.mutations)) throw new Error("CAPABILITY_METADATA_INVALID");
        this.#cache = { value, receivedAt: this.now() };
        return value;
      }).finally(() => { this.#refresh = undefined; });
    }
    try { return await this.#refresh; } catch (error) {
      if (allowStale && this.#cache && this.now() - this.#cache.receivedAt <= 300_000) return this.#cache.value;
      if (error instanceof Error && error.message === "CAPABILITY_METADATA_INVALID") throw error;
      throw new Error("CAPABILITY_METADATA_UNAVAILABLE", { cause: error });
    }
  }
}
