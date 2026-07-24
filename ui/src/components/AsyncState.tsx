export function LoadingState({ label = "Loading…" }: { label?: string }) { return <p role="status" aria-live="polite">{label}</p>; }
export function EmptyState({ message }: { message: string }) { return <p role="status">{message}</p>; }
export function UnavailableState({ message = "This service is temporarily unavailable.", onRetry }: { message?: string; onRetry?: () => void }) { return <div role="alert"><p>{message}</p>{onRetry && <button type="button" onClick={onRetry}>Retry</button>}</div>; }
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) { return <div role="alert"><p>{message}</p>{onRetry && <button type="button" onClick={onRetry}>Retry</button>}</div>; }
