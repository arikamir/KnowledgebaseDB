import { authenticationEpoch } from "../app/auth-epoch";
import { submittedOperations } from "../app/submitted-operation-registry";

export function SignOutAction({ onSignOut }: { onSignOut: () => Promise<void> }) {
  async function signOut() {
    authenticationEpoch.invalidate();
    submittedOperations.clear();
    await onSignOut();
  }
  return <button type="button" onClick={() => void signOut()}>Sign out</button>;
}
