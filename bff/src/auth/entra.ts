import { createHash, randomBytes } from "node:crypto";

export function canonicalizeReturnTarget(value: string | undefined): string {
  if (!value) return "/";
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\") || value.includes("#") || [...value].some((character) => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127)) return "/";
  let decoded: string;
  try { decoded = decodeURIComponent(value); } catch { return "/"; }
  if (!decoded.startsWith("/") || decoded.startsWith("//") || decoded.includes("\\") || decoded.includes("#")) return "/";
  return decoded;
}

export interface AuthorizationRequest {
  state: string;
  nonce: string;
  codeVerifier: string;
  codeChallenge: string;
  returnTo: string;
}

export function createAuthorizationRequest(returnTarget?: string): AuthorizationRequest {
  const codeVerifier = randomBytes(32).toString("base64url");
  return {
    state: randomBytes(32).toString("base64url"),
    nonce: randomBytes(32).toString("base64url"),
    codeVerifier,
    codeChallenge: createHash("sha256").update(codeVerifier).digest("base64url"),
    returnTo: canonicalizeReturnTarget(returnTarget),
  };
}
