import type { FastifyRequest } from "fastify";

export function requireContractVersion(request: FastifyRequest, supportedMajor = 1): void {
  const supplied = request.headers["x-ui-contract-version"];
  if (typeof supplied !== "string" || !new RegExp(`^${supportedMajor}\\.\\d+\\.\\d+$`).test(supplied)) {
    throw Object.assign(new Error("CONTRACT_VERSION_UNSUPPORTED"), { statusCode: 409 });
  }
}
