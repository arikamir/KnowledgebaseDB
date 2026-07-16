import { authenticationEpoch } from "./auth-epoch";

export type OperationResolution<T> =
  | { state: "saved"; value: T }
  | { state: "failed_to_save"; error: unknown }
  | { state: "save_unknown"; error: unknown };

interface ActiveOperation<T> {
  key: string;
  intentDigest: string;
  epoch: number;
  promise: Promise<OperationResolution<T>>;
}

export class SubmittedOperationRegistry {
  #operations = new Map<string, ActiveOperation<unknown>>();
  #keys = new Map<string, { intentDigest: string; key: string }>();
  #unknown = new Map<string, { intentDigest: string; key: string }>();

  keyFor(action: string, intentDigest: string): string {
    const current = this.#keys.get(action);
    if (current?.intentDigest === intentDigest) return current.key;
    if (current) throw new Error("OPERATION_INTENT_CHANGED");
    const key = crypto.randomUUID();
    this.#keys.set(action, { intentDigest, key });
    return key;
  }

  submit<T>(
    action: string,
    intentDigest: string,
    key: string,
    execute: (key: string) => Promise<T>,
  ): Promise<OperationResolution<T>> {
    const current = this.#operations.get(action) as ActiveOperation<T> | undefined;
    if (current) {
      if (current.intentDigest !== intentDigest) throw new Error("OPERATION_INTENT_CHANGED");
      return current.promise;
    }
    const epoch = authenticationEpoch.capture();
    const promise = execute(key)
      .then((value): OperationResolution<T> => {
        if (!authenticationEpoch.isCurrent(epoch)) throw new Error("STALE_AUTHENTICATION_EPOCH");
        return { state: "saved", value };
      })
      .catch((error: unknown): OperationResolution<T> => {
        const code = error instanceof Error ? error.message : "";
        if (code === "STALE_AUTHENTICATION_EPOCH") return { state: "failed_to_save", error };
        if (/timeout|network|CORE_UNAVAILABLE|CAPABILITY_METADATA_UNAVAILABLE|SESSION_DEPENDENCY_UNAVAILABLE/i.test(code)) return { state: "save_unknown", error };
        return { state: "failed_to_save", error };
      })
      .then((result) => {
        if (result.state === "save_unknown") this.#unknown.set(action, { intentDigest, key });
        else this.#keys.delete(action);
        return result;
      })
      .finally(() => { this.#operations.delete(action); });
    this.#operations.set(action, { key, intentDigest, epoch, promise });
    return promise;
  }

  blocksNavigation(): boolean { return this.#operations.size > 0; }
  async resolveUnknown<T>(action: string, check: (key: string) => Promise<T | null>): Promise<OperationResolution<T>> {
    const unknown = this.#unknown.get(action);
    if (!unknown) throw new Error("NO_UNKNOWN_OPERATION");
    try {
      const value = await check(unknown.key);
      if (value === null) return { state: "save_unknown", error: new Error("RESULT_STILL_UNKNOWN") };
      this.#unknown.delete(action); this.#keys.delete(action);
      return { state: "saved", value };
    } catch (error) { return { state: "save_unknown", error }; }
  }
  clear(): void { this.#operations.clear(); this.#keys.clear(); this.#unknown.clear(); }
}

export const submittedOperations = new SubmittedOperationRegistry();
