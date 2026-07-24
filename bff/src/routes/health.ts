import type { FastifyPluginAsync } from "fastify";
import { readFile } from "node:fs/promises";
import { X509Certificate, createPrivateKey, createPublicKey } from "node:crypto";

async function mountedClientCertificateReady(path: string | undefined, expectedVersion: string | undefined): Promise<boolean> {
  if (!path || !expectedVersion) return false;
  try {
    const pem = await readFile(path, "utf8");
    const certificatePem = pem.match(/-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----/)?.[0];
    const privateKeyPem = pem.match(/-----BEGIN (?:RSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA )?PRIVATE KEY-----/)?.[0];
    if (!certificatePem || !privateKeyPem) return false;
    const certificate = new X509Certificate(certificatePem);
    const privateKey = createPrivateKey(privateKeyPem);
    const certificatePublicKey = certificate.publicKey.export({ type: "spki", format: "der" });
    const privatePublicKey = createPublicKey({
      key: privateKey.export({ type: "pkcs8", format: "pem" }),
      format: "pem",
    }).export({ type: "spki", format: "der" });
    const now = Date.now();
    return certificatePublicKey.equals(privatePublicKey)
      && Date.parse(certificate.validFrom) <= now
      && Date.parse(certificate.validTo) > now;
  } catch {
    return false;
  }
}

async function mountedTrustBundleReady(path: string | undefined, expectedVersion: string | undefined): Promise<boolean> {
  if (!path || !expectedVersion) return false;
  try {
    const certificate = new X509Certificate(await readFile(path, "utf8"));
    const now = Date.now();
    return Date.parse(certificate.validFrom) <= now && Date.parse(certificate.validTo) > now;
  } catch {
    return false;
  }
}

export const healthRoutes: FastifyPluginAsync = async (app) => {
  app.get("/health/live", async () => ({ status: "ok" }));
  app.get("/health/ready", async (_request, reply) => {
    const configured = (app as unknown as { readinessChecks?: Record<string, () => Promise<boolean>> }).readinessChecks ?? {};
    const checks: Record<string, () => Promise<boolean>> = { ...configured };
    if (process.env.BFF_CLIENT_CERTIFICATE_PATH || process.env.BFF_CLIENT_CERTIFICATE_VERSION) {
      checks["bff-client-certificate"] = () => mountedClientCertificateReady(
        process.env.BFF_CLIENT_CERTIFICATE_PATH,
        process.env.BFF_CLIENT_CERTIFICATE_VERSION,
      );
    }
    if (process.env.CORE_CA_BUNDLE_PATH || process.env.CORE_CA_CERTIFICATE_VERSION) {
      checks["core-tls"] = () => mountedTrustBundleReady(
        process.env.CORE_CA_BUNDLE_PATH,
        process.env.CORE_CA_CERTIFICATE_VERSION,
      );
    }
    const required = (process.env.READINESS_REQUIRED_DEPENDENCIES ?? "")
      .split(",").map((name) => name.trim()).filter(Boolean);
    const failed: string[] = [];
    for (const name of required) if (!(name in checks)) failed.push(name);
    for (const [name, check] of Object.entries(checks)) {
      try { if (!await check()) failed.push(name); } catch { failed.push(name); }
    }
    if (failed.length) return reply.code(503).send({ status: "unready", failedDependencies: failed });
    return { status: "ready" };
  });
};
