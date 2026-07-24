import { useCallback, useState } from "react";
import { submittedOperations, type OperationResolution } from "./submitted-operation-registry";

export function useSubmittedOperation<T>() {
  const [resolution, setResolution] = useState<OperationResolution<T> | null>(null);
  const submit = useCallback(async (action: string, intentDigest: string, key: string, execute: (key: string) => Promise<T>) => {
    const result = await submittedOperations.submit(action, intentDigest, key, execute);
    setResolution(result);
    return result;
  }, []);
  return { submit, resolution, pending: submittedOperations.blocksNavigation() };
}
