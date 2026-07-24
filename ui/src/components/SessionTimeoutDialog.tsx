import { useEffect, useState } from "react";

export interface SessionTimeoutDialogProps {
  idleExpiresAt?: string;
  absoluteExpiresAt?: string;
  onContinue: () => Promise<void>;
  onExpired: () => void;
  now?: () => number;
}

export function SessionTimeoutDialog({ idleExpiresAt, absoluteExpiresAt, onContinue, onExpired, now = Date.now }: SessionTimeoutDialogProps) {
  const [, refresh] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => refresh((value) => value + 1), 1_000);
    return () => window.clearInterval(timer);
  }, []);
  if (!idleExpiresAt || !absoluteExpiresAt) return null;
  const idle = new Date(idleExpiresAt).getTime();
  const absolute = new Date(absoluteExpiresAt).getTime();
  const deadline = Math.min(idle, absolute);
  const remaining = deadline - now();
  if (remaining <= 0) { queueMicrotask(onExpired); return null; }
  if (remaining > 120_000) return null;
  const absoluteEnding = absolute <= idle;
  return (
    <div className="timeout-dialog" role="dialog" aria-modal="true" aria-labelledby="timeout-title">
      <h2 id="timeout-title">Your session is ending</h2>
      <p>{absoluteEnding ? "The eight-hour absolute session limit cannot be extended." : "Your idle session expires soon. Continue to remain signed in."}</p>
      {!absoluteEnding && <button type="button" onClick={() => void onContinue()}>Continue session</button>}
    </div>
  );
}
