import { useRef, useState, type FormEvent } from "react";
import type { PersistenceSnapshot } from "../../app/persistence-state";
import { PersistenceStatus } from "../../components/PersistenceStatus";
import type { ProblemDetails } from "../../contracts/bff-api";

export interface ProgressInput {
  roadmapId: string;
  notes: string;
  completedSteps: string;
  completedMilestoneKeys: string;
  newGoals: string;
}

interface Props {
  input: ProgressInput;
  onChange: (value: ProgressInput) => void;
  onSubmit: () => Promise<void>;
  persistence: PersistenceSnapshot;
  problem: ProblemDetails | null;
}

export function ProgressForm({ input, onChange, onSubmit, persistence, problem }: Props) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const roadmapRef = useRef<HTMLInputElement>(null);
  const inputsBlocked = persistence.state === "saving" || persistence.state === "save_unknown";
  const serverError = (field: string) => problem?.fieldErrors?.find((item) => item.field === field)?.messages[0];

  function submit(event: FormEvent) {
    event.preventDefault();
    performance.mark("progress.validation.attempt");
    const next: Record<string, string> = {};
    if (!input.roadmapId.trim()) next.roadmapId = "Enter a roadmap reference.";
    const keys = input.completedMilestoneKeys.split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
    if (keys.some((key) => !/^[a-z0-9][a-z0-9._-]{2,127}$/.test(key))) {
      next.completedMilestoneKeys = "Use lowercase milestone keys with letters, numbers, dots, underscores, or hyphens.";
    }
    setErrors(next);
    if (Object.keys(next).length) {
      performance.mark("progress.validation.guidance-committed");
      roadmapRef.current?.focus();
      return;
    }
    void onSubmit();
  }

  const roadmapError = errors.roadmapId ?? serverError("roadmapId");
  const keyError = errors.completedMilestoneKeys ?? serverError("completedMilestoneKeys");
  const showSummary = Boolean(problem || Object.keys(errors).length);
  return <form onSubmit={submit} noValidate>
    <h2>Record progress</h2>
    {showSummary && <div className="error-summary" role="alert" tabIndex={-1}>
      <h3>Check your progress update</h3>
      <p>{problem?.detail ?? Object.values(errors)[0] ?? "Correct the highlighted field."}</p>
    </div>}
    <label>Roadmap reference
      <input ref={roadmapRef} required disabled={inputsBlocked} value={input.roadmapId}
        aria-invalid={Boolean(roadmapError)} aria-describedby={roadmapError ? "progress-roadmap-error" : undefined}
        onChange={(event) => onChange({ ...input, roadmapId: event.target.value })} />
    </label>
    {roadmapError && <p id="progress-roadmap-error" role="alert">{roadmapError}</p>}
    <label>Progress notes
      <textarea disabled={inputsBlocked} value={input.notes} onChange={(event) => onChange({ ...input, notes: event.target.value })} />
    </label>
    <label>Completed milestone titles or skill areas
      <textarea disabled={inputsBlocked} value={input.completedSteps} onChange={(event) => onChange({ ...input, completedSteps: event.target.value })} />
    </label>
    <label>Completed milestone keys
      <textarea disabled={inputsBlocked} value={input.completedMilestoneKeys}
        aria-invalid={Boolean(keyError)} aria-describedby={keyError ? "progress-keys-error" : undefined}
        onChange={(event) => onChange({ ...input, completedMilestoneKeys: event.target.value })} />
    </label>
    {keyError && <p id="progress-keys-error" role="alert">{keyError}</p>}
    <label>New goals
      <textarea disabled={inputsBlocked} value={input.newGoals} onChange={(event) => onChange({ ...input, newGoals: event.target.value })} />
    </label>
    <button type="submit" disabled={persistence.state === "saving"}>{problem?.retryable ? "Retry progress" : "Record progress"}</button>
    <PersistenceStatus snapshot={persistence} />
  </form>;
}
