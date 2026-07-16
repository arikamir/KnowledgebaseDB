export class CoreUnavailable extends Error { readonly code = "CORE_UNAVAILABLE"; }

export interface CoreRequestOptions extends RequestInit {
  idempotencyKey?: string;
  mutationDispatched?: boolean;
  timeoutMs?: number;
}

export async function coreRequest(
  url: URL,
  options: CoreRequestOptions,
  fetcher: typeof fetch = fetch,
  sleep: (milliseconds: number) => Promise<void> = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
): Promise<Response> {
  const method = (options.method ?? "GET").toUpperCase();
  const safeRead = method === "GET" || method === "HEAD";
  const maxAttempts = safeRead ? 3 : options.mutationDispatched && options.idempotencyKey ? 2 : 1;
  const delays = [250, 1_000];
  let lastError: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? 10_000);
    try {
      const response = await fetcher(url, { ...options, signal: controller.signal, headers: { ...options.headers, ...(options.idempotencyKey ? { "Idempotency-Key": options.idempotencyKey } : {}) } });
      if (response.status < 500 || attempt + 1 >= maxAttempts) return response;
      lastError = new Error(`core ${response.status}`);
    } catch (error) { lastError = error; } finally { clearTimeout(timeout); }
    if (attempt < maxAttempts - 1) await sleep(delays[attempt]);
  }
  throw new CoreUnavailable("CORE_UNAVAILABLE", { cause: lastError });
}
