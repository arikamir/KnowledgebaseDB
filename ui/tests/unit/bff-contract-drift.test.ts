import { execFileSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { BFF_CONTRACT_DIGEST, BFF_OPERATIONS } from "../../src/contracts/bff-api";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

describe("BFF contract generation", () => {
  it("is digest bound and drift free", () => {
    expect(BFF_CONTRACT_DIGEST).toMatch(/^[a-f0-9]{64}$/);
    expect(BFF_OPERATIONS.length).toBeGreaterThan(10);
    expect(() => execFileSync(resolve(root, ".venv/bin/python"), [resolve(root, "scripts/ci/generate_contracts.py"), "--check"])).not.toThrow();
  });
});
