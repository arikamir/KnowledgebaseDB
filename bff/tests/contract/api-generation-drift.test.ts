import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");

describe("generated API contracts", () => {
  it("have no checked-in drift", () => {
    expect(() => execFileSync(resolve(root, ".venv/bin/python"), [resolve(root, "scripts/ci/generate_contracts.py"), "--check"])).not.toThrow();
  });
});
