import { describe, expect, it } from "vitest";
import { PersistenceMachine } from "../../src/app/persistence-state";

describe("persistence state", () => {
  it("exposes all exact states and blocks navigation only while unresolved", () => {
    const machine = new PersistenceMachine();
    expect(machine.snapshot.state).toBe("not_yet_saved");
    expect(machine.begin()).toMatchObject({ state: "saving", blocksNavigation: true });
    expect(machine.requestNavigation()).toEqual({ allowed: false, checkAuthoritativeState: false });
    expect(machine.requestNavigation(true)).toEqual({ allowed: true, checkAuthoritativeState: true });
    expect(machine.uncertain()).toMatchObject({ state: "save_unknown", blocksNavigation: true });
    expect(machine.fail()).toMatchObject({ state: "failed_to_save", blocksNavigation: false });
    expect(machine.succeed()).toMatchObject({ state: "saved", blocksNavigation: false });
  });
});
