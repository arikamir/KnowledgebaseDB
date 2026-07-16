import { describe, expect, it } from "vitest";
import { AuthenticationEpoch, authenticationEpoch } from "../../src/app/auth-epoch";
import { restoreAuthoritativeState } from "../../src/app/restore-persisted-state";
import { bffRequest, StaleAuthenticationResponseError } from "../../src/bff/client";

describe("authentication epoch restoration", () => {
  it("rejects a delayed pre-logout response", async () => {
    let respond!: (response: Response) => void;
    const pending = bffRequest<{ authenticated: boolean }>("/bff/v1/session", {}, () => new Promise((resolve) => { respond = resolve; }));
    authenticationEpoch.invalidate();
    respond(new Response(JSON.stringify({ authenticated: true }), { status: 200 }));
    await expect(pending).rejects.toBeInstanceOf(StaleAuthenticationResponseError);
  });

  it("discards browser input and reloads only authoritative state", async () => {
    const restored = await restoreAuthoritativeState(async () => ({ id: "saved-roadmap" }));
    expect(restored.value).toEqual({ id: "saved-roadmap" });
    expect(restored.notice).toContain("Unsaved browser input was discarded");
  });

  it("invalidates captured epochs on sign-out or emergency reauthentication", () => {
    const epoch = new AuthenticationEpoch();
    const captured = epoch.capture();
    epoch.invalidate();
    expect(epoch.isCurrent(captured)).toBe(false);
  });
});
