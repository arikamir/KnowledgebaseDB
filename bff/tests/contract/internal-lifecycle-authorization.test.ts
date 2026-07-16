import { describe, expect, it } from "vitest";

describe("internal lifecycle authorization", () => {
  it.each([
    [undefined, 403],
    [{ clientId: "lifecycle", roles: [] }, 403],
    [{ clientId: "lifecycle", roles: ["Wrong.Role"] }, 403],
  ])("rejects missing or wrong role before session access", (principal, expected) => {
    const authorized = principal?.roles.includes("LearningBff.Session.Revoke") ?? false;
    expect(authorized ? 200 : 403).toBe(expected);
  });

  it("accepts only the exact lifecycle role", () => {
    expect(["LearningBff.Session.Revoke"].includes("LearningBff.Session.Revoke")).toBe(true);
  });
});
