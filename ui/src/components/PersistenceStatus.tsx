import type { PersistenceSnapshot } from "../app/persistence-state";

export function PersistenceStatus({ snapshot }: { snapshot: PersistenceSnapshot }) {
  return <p role="status" aria-live="polite" data-state={snapshot.state}>{snapshot.message}</p>;
}
