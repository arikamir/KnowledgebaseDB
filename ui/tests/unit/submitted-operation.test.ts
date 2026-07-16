import { describe, expect, it, vi } from "vitest";
import { SubmittedOperationRegistry } from "../../src/app/submitted-operation-registry";

describe("submitted operation registry", () => {
  it("suppresses duplicate submissions and reuses the same key", async () => {
    const registry = new SubmittedOperationRegistry();
    let resolve!: (value: string) => void;
    const execute = vi.fn(() => new Promise<string>((done) => { resolve = done; }));
    const first = registry.submit("create-roadmap", "intent-a", "key-a", execute);
    const duplicate = registry.submit("create-roadmap", "intent-a", "key-a", execute);
    expect(first).toBe(duplicate);
    expect(registry.blocksNavigation()).toBe(true);
    resolve("saved");
    await expect(first).resolves.toEqual({ state: "saved", value: "saved" });
    expect(execute).toHaveBeenCalledOnce();
    expect(execute).toHaveBeenCalledWith("key-a");
  });

  it("rejects a corrected intent until the active action resolves", async () => {
    const registry = new SubmittedOperationRegistry();
    let resolve!: (value: string) => void;
    const pending = registry.submit("save", "old", "key-old", () => new Promise((done) => { resolve = done; }));
    expect(() => registry.submit("save", "new", "key-new", async () => "new")).toThrow("OPERATION_INTENT_CHANGED");
    resolve("old");
    await pending;
  });

  it("classifies timeout as save_unknown for same-key recovery", async () => {
    const registry = new SubmittedOperationRegistry();
    const key = registry.keyFor("save", "same");
    expect(registry.keyFor("save", "same")).toBe(key);
    await expect(registry.submit("save", "same", key, async () => { throw new Error("timeout after dispatch"); }))
      .resolves.toMatchObject({ state: "save_unknown" });
    await expect(registry.resolveUnknown("save", async (replayedKey) => replayedKey === key ? "saved" : null))
      .resolves.toEqual({ state: "saved", value: "saved" });
  });
});
