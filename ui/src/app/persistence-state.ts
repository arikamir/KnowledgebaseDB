export type PersistenceState = "not_yet_saved" | "saving" | "save_unknown" | "failed_to_save" | "saved";

export interface PersistenceSnapshot {
  state: PersistenceState;
  message: string;
  blocksNavigation: boolean;
}

const SNAPSHOTS: Record<PersistenceState, PersistenceSnapshot> = {
  not_yet_saved: { state: "not_yet_saved", message: "Not yet saved", blocksNavigation: false },
  saving: { state: "saving", message: "Saving…", blocksNavigation: true },
  save_unknown: { state: "save_unknown", message: "Checking whether your work was saved…", blocksNavigation: true },
  failed_to_save: { state: "failed_to_save", message: "Not saved. Your input is still available.", blocksNavigation: false },
  saved: { state: "saved", message: "Saved", blocksNavigation: false },
};

export class PersistenceMachine {
  #state: PersistenceState = "not_yet_saved";

  get snapshot(): PersistenceSnapshot { return SNAPSHOTS[this.#state]; }
  begin(): PersistenceSnapshot { this.#state = "saving"; return this.snapshot; }
  uncertain(): PersistenceSnapshot { this.#state = "save_unknown"; return this.snapshot; }
  fail(): PersistenceSnapshot { this.#state = "failed_to_save"; return this.snapshot; }
  succeed(): PersistenceSnapshot { this.#state = "saved"; return this.snapshot; }
  reset(): PersistenceSnapshot { this.#state = "not_yet_saved"; return this.snapshot; }

  requestNavigation(cancelAndCheck = false): { allowed: boolean; checkAuthoritativeState: boolean } {
    if (!this.snapshot.blocksNavigation) return { allowed: true, checkAuthoritativeState: false };
    return cancelAndCheck
      ? { allowed: true, checkAuthoritativeState: true }
      : { allowed: false, checkAuthoritativeState: false };
  }
}
