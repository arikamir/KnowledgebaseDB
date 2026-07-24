import type { EncryptedValue } from "./encryption-key-ring.js";
import { EncryptionKeyRing } from "./encryption-key-ring.js";

export class SessionDependencyUnavailable extends Error { readonly code = "SESSION_DEPENDENCY_UNAVAILABLE"; }

export interface SessionData {
  sessionId: string;
  ownerKey: string;
  csrfToken: string;
  issuedAt: string;
  lastSeenAt: string;
  idleExpiresAt: string;
  absoluteExpiresAt: string;
  revokedAt?: string;
}

export interface SessionBackend {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
  del(key: string): Promise<void>;
  addOwnerSession(ownerKey: string, sessionId: string): Promise<void>;
  ownerSessions(ownerKey: string): Promise<string[]>;
  addKeySession(keyVersion: string, sessionId: string): Promise<void>;
  keySessions(keyVersion: string): Promise<string[]>;
}

export class EncryptedSessionStore {
  constructor(
    private readonly backend: SessionBackend,
    private readonly keys: EncryptionKeyRing,
    private readonly sleep: (milliseconds: number) => Promise<void> = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
  ) {}

  async save(session: SessionData): Promise<void> {
    await this.#attempt(async () => {
      await this.backend.set(`session:${session.sessionId}`, JSON.stringify(this.keys.encrypt(session)));
      await this.backend.addOwnerSession(session.ownerKey, session.sessionId);
      await this.backend.addKeySession(this.keys.activeVersion, session.sessionId);
    });
  }

  async load(sessionId: string): Promise<SessionData | null> {
    return this.#attempt(async () => {
      const encoded = await this.backend.get(`session:${sessionId}`);
      if (encoded === null) return null;
      const decrypted = this.keys.decrypt<SessionData>(JSON.parse(encoded) as EncryptedValue);
      if (decrypted.requiresRewrite) await this.backend.set(`session:${sessionId}`, JSON.stringify(this.keys.encrypt(decrypted.value)));
      return decrypted.value;
    });
  }

  async revoke(sessionId: string): Promise<void> { await this.#attempt(() => this.backend.del(`session:${sessionId}`)); }

  async revokeOwner(ownerKey: string): Promise<number> {
    return this.#attempt(async () => {
      const sessions = await this.backend.ownerSessions(ownerKey);
      await Promise.all(sessions.map((sessionId) => this.backend.del(`session:${sessionId}`)));
      return sessions.length;
    });
  }

  async revokeKeyVersion(keyVersion: string): Promise<number> {
    return this.#attempt(async () => {
      const sessions = await this.backend.keySessions(keyVersion);
      await Promise.all(sessions.map((sessionId) => this.backend.del(`session:${sessionId}`)));
      return sessions.length;
    });
  }

  async #attempt<T>(operation: () => Promise<T>): Promise<T> {
    const delays = [100, 500] as const;
    let lastError: unknown;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try { return await operation(); } catch (error) {
        lastError = error;
        if (attempt < delays.length) await this.sleep(delays[attempt]);
      }
    }
    throw new SessionDependencyUnavailable("SESSION_DEPENDENCY_UNAVAILABLE", { cause: lastError });
  }
}
