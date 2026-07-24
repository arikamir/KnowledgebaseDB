import { CORE_CONTRACT_DIGEST, CORE_OPERATIONS, type CoreOperationId } from "../contracts/core-api.js";

export interface CoreClientOptions {
  baseUrl: string;
  fetcher?: typeof fetch;
  accessToken: () => Promise<string>;
}

export class CoreClient {
  readonly #fetcher: typeof fetch;
  constructor(private readonly options: CoreClientOptions) { this.#fetcher = options.fetcher ?? fetch; }

  async request<T>(operationId: CoreOperationId, init: RequestInit & { path: string }): Promise<T> {
    if (!CORE_OPERATIONS.some((operation) => operation.operationId === operationId)) throw new Error("UNKNOWN_CORE_OPERATION");
    const token = await this.options.accessToken();
    const response = await this.#fetcher(new URL(init.path, this.options.baseUrl), {
      ...init,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
        "X-Core-Contract-Digest": CORE_CONTRACT_DIGEST,
        ...init.headers,
      },
    });
    if (!response.ok) throw Object.assign(new Error("CORE_REQUEST_FAILED"), { status: response.status });
    return response.json() as Promise<T>;
  }
}
