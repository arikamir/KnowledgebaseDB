import { authenticationEpoch } from "../app/auth-epoch";
import type { ProblemDetails } from "../contracts/bff-api";

export class StaleAuthenticationResponseError extends Error {}

export async function bffRequest<T>(
  path: `/bff/v1/${string}`,
  init: RequestInit = {},
  fetcher: typeof fetch = fetch,
): Promise<T> {
  const epoch = authenticationEpoch.capture();
  const response = await fetcher(path, {
    ...init,
    credentials: "same-origin",
    headers: { Accept: "application/json", ...init.headers },
  });
  if (!authenticationEpoch.isCurrent(epoch)) throw new StaleAuthenticationResponseError();
  if (!response.ok) {
    const problem = await response.json() as ProblemDetails;
    throw Object.assign(new Error(problem.code), { problem });
  }
  return response.json() as Promise<T>;
}
