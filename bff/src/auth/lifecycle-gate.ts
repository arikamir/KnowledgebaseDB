export type LifecycleDecision = "active" | "departed" | "unknown";

export interface LifecycleClient {
  bootstrap(tenantId: string, objectId: string): Promise<{ status: LifecycleDecision; employeeId?: string }>;
}

export async function approveSessionActivation(client: LifecycleClient, tenantId: string, objectId: string): Promise<string> {
  let result: Awaited<ReturnType<LifecycleClient["bootstrap"]>>;
  try { result = await client.bootstrap(tenantId, objectId); } catch { throw new Error("CORE_UNAVAILABLE"); }
  if (result.status !== "active" || !result.employeeId) throw new Error(result.status === "departed" ? "EMPLOYEE_ACCESS_DENIED" : "IDENTITY_NOT_RECOGNIZED");
  return result.employeeId;
}
