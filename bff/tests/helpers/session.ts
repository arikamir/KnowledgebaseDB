import type { SessionBackend } from "../../src/sessions/session-store.js";

export class MemorySessionBackend implements SessionBackend {
  values = new Map<string, string>();
  owners = new Map<string, Set<string>>();
  fail = false;
  calls = 0;
  async get(key: string) { this.hit(); return this.values.get(key) ?? null; }
  async set(key: string, value: string) { this.hit(); this.values.set(key, value); }
  async del(key: string) { this.hit(); this.values.delete(key); }
  async addOwnerSession(ownerKey: string, sessionId: string) { this.hit(); const values = this.owners.get(ownerKey) ?? new Set(); values.add(sessionId); this.owners.set(ownerKey, values); }
  async ownerSessions(ownerKey: string) { this.hit(); return [...(this.owners.get(ownerKey) ?? [])]; }
  private hit() { this.calls += 1; if (this.fail) throw new Error("redis unavailable"); }
}
