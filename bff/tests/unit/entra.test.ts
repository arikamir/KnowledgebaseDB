import { describe, expect, it } from "vitest";
import { canonicalizeReturnTarget, createAuthorizationRequest } from "../../src/auth/entra.js";

describe("Entra authorization request", () => {
  it("creates opaque state, nonce, and an S256 PKCE challenge", () => {
    const request = createAuthorizationRequest("/roadmaps");
    expect(request.returnTo).toBe("/roadmaps");
    expect(request.state).not.toBe(request.nonce);
    expect(request.codeVerifier.length).toBeGreaterThan(32);
    expect(request.codeChallenge).toMatch(/^[A-Za-z0-9_-]+$/);
  });

  it("canonicalizes return targets before including them in transient state", () => {
    expect(canonicalizeReturnTarget("https://evil.test")).toBe("/");
  });
});
