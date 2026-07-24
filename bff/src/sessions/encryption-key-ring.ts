import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

export interface EncryptionKeyVersion {
  version: string;
  key: Buffer;
  mode: "active" | "decrypt_only";
}

export interface EncryptedValue {
  keyVersion: string;
  iv: string;
  ciphertext: string;
  authTag: string;
}

export class EncryptionKeyRing {
  readonly #keys = new Map<string, EncryptionKeyVersion>();
  readonly #active: EncryptionKeyVersion;

  constructor(keys: readonly EncryptionKeyVersion[]) {
    const active = keys.filter((key) => key.mode === "active");
    if (active.length !== 1) throw new Error("KEY_MATERIAL_UNAVAILABLE");
    for (const key of keys) {
      if (key.key.length !== 32 || this.#keys.has(key.version)) throw new Error("KEY_MATERIAL_UNAVAILABLE");
      this.#keys.set(key.version, key);
    }
    this.#active = active[0];
  }

  get activeVersion(): string { return this.#active.version; }

  encrypt(value: unknown): EncryptedValue {
    const iv = randomBytes(12);
    const cipher = createCipheriv("aes-256-gcm", this.#active.key, iv);
    const ciphertext = Buffer.concat([cipher.update(JSON.stringify(value), "utf8"), cipher.final()]);
    return { keyVersion: this.#active.version, iv: iv.toString("base64url"), ciphertext: ciphertext.toString("base64url"), authTag: cipher.getAuthTag().toString("base64url") };
  }

  decrypt<T>(value: EncryptedValue): { value: T; requiresRewrite: boolean } {
    const key = this.#keys.get(value.keyVersion);
    if (!key) throw new Error("SESSION_KEY_RETIRED");
    const decipher = createDecipheriv("aes-256-gcm", key.key, Buffer.from(value.iv, "base64url"));
    decipher.setAuthTag(Buffer.from(value.authTag, "base64url"));
    const plaintext = Buffer.concat([decipher.update(Buffer.from(value.ciphertext, "base64url")), decipher.final()]);
    return { value: JSON.parse(plaintext.toString("utf8")) as T, requiresRewrite: key.version !== this.#active.version };
  }
}
