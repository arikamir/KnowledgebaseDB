import { authenticationEpoch } from "./auth-epoch";

export interface RestoreResult<T> {
  value: T | null;
  notice?: string;
  epoch: number;
}

export async function restoreAuthoritativeState<T>(loader: () => Promise<T | null>): Promise<RestoreResult<T>> {
  const epoch = authenticationEpoch.capture();
  const value = await loader();
  if (!authenticationEpoch.isCurrent(epoch)) return { value: null, epoch };
  return { value, notice: "Unsaved browser input was discarded; authoritative saved state was reloaded.", epoch };
}
