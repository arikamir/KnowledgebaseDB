import { createHash, randomBytes } from "node:crypto";
import { ConfidentialClientApplication, type Configuration } from "@azure/msal-node";

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

export interface EntraConfidentialClientConfig {
  clientId: string;
  tenantId: string;
  redirectUri: string;
  coreScope: string;
  certificateThumbprint: string;
  certificatePrivateKey: string;
}

export interface AuthorizationCodeResult {
  tenantId: string;
  objectId: string;
  accessToken: string;
  expiresOn: Date;
}

export class EntraAuthorizationCodeClient {
  readonly #client: ConfidentialClientApplication;
  constructor(private readonly config: EntraConfidentialClientConfig, client?: ConfidentialClientApplication) {
    const msal: Configuration = {
      auth: {
        clientId: config.clientId,
        authority: `https://login.microsoftonline.com/${config.tenantId}`,
        clientCertificate: { thumbprint: config.certificateThumbprint, privateKey: config.certificatePrivateKey },
      },
    };
    this.#client = client ?? new ConfidentialClientApplication(msal);
  }

  async authorizationUrl(request: AuthorizationRequest): Promise<string> {
    return this.#client.getAuthCodeUrl({
      scopes: [this.config.coreScope], redirectUri: this.config.redirectUri,
      state: request.state, nonce: request.nonce, codeChallenge: request.codeChallenge,
      codeChallengeMethod: "S256",
    });
  }

  async exchange(code: string, request: AuthorizationRequest): Promise<AuthorizationCodeResult> {
    const response = await this.#client.acquireTokenByCode({
      code, scopes: [this.config.coreScope], redirectUri: this.config.redirectUri,
      codeVerifier: request.codeVerifier,
    });
    const claims = response.idTokenClaims as Record<string, unknown> | undefined;
    const tenantId = claims?.tid;
    const objectId = claims?.oid;
    if (tenantId !== this.config.tenantId || typeof objectId !== "string" || !objectId || !response.accessToken || !response.expiresOn) {
      throw new Error("ENTRA_CODE_EXCHANGE_INVALID");
    }
    return { tenantId, objectId, accessToken: response.accessToken, expiresOn: response.expiresOn };
  }
}
