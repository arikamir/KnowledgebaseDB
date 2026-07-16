import type { SessionBackend } from "./session-store.js";

export interface RedisConnection {
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<unknown>;
  del(key: string): Promise<unknown>;
  sadd(key: string, value: string): Promise<unknown>;
  smembers(key: string): Promise<string[]>;
  quit(): Promise<unknown>;
}

export interface RedisEntraConnector {
  acquireToken(): Promise<string>;
  connect(accessToken: string): Promise<RedisConnection>;
}

export class RedisSessionBackend implements SessionBackend {
  #connection?: RedisConnection;
  constructor(private readonly connector: RedisEntraConnector) {}

  async get(key: string) { return (await this.#client()).get(key); }
  async set(key: string, value: string) { await (await this.#client()).set(key, value); }
  async del(key: string) { await (await this.#client()).del(key); }
  async addOwnerSession(ownerKey: string, sessionId: string) { await (await this.#client()).sadd(`owner:${ownerKey}`, sessionId); }
  async ownerSessions(ownerKey: string) { return (await this.#client()).smembers(`owner:${ownerKey}`); }
  async addKeySession(keyVersion: string, sessionId: string) { await (await this.#client()).sadd(`key-version:${keyVersion}`, sessionId); }
  async keySessions(keyVersion: string) { return (await this.#client()).smembers(`key-version:${keyVersion}`); }

  async reconnect(): Promise<void> {
    if (this.#connection) await this.#connection.quit();
    this.#connection = undefined;
    await this.#client();
  }

  async #client(): Promise<RedisConnection> {
    if (!this.#connection) {
      const token = await this.connector.acquireToken();
      if (!token) throw new Error("SESSION_DEPENDENCY_UNAVAILABLE");
      this.#connection = await this.connector.connect(token);
    }
    return this.#connection;
  }
}
