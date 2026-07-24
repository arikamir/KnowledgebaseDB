import { useEffect, useRef, useState, type FormEvent } from "react";
import { PersistenceStatus } from "../../components/PersistenceStatus";
import type { RoadmapInput } from "./useRoadmap";
import type { PersistenceSnapshot } from "../../app/persistence-state";

export function RoadmapForm({ input, onChange, onSubmit, persistence }: { input: RoadmapInput; onChange: (value: RoadmapInput) => void; onSubmit: () => Promise<void>; persistence: PersistenceSnapshot }) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const roleRef = useRef<HTMLInputElement>(null);
  const levelRef = useRef<HTMLSelectElement>(null);
  const targetRef = useRef<HTMLInputElement>(null);
  const hoursRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const first = [
      ["role", roleRef], ["experienceLevel", levelRef], ["targetRole", targetRef], ["availableTimePerWeek", hoursRef],
    ].find(([name]) => Boolean(errors[String(name)]));
    if (first) (first[1] as typeof roleRef).current?.focus();
  }, [errors]);
  function submit(event: FormEvent) {
    event.preventDefault();
    performance.mark("career.validation.attempt");
    const nextErrors: Record<string, string> = {};
    if (!input.role.trim()) nextErrors.role = "Enter your current role.";
    if (!input.experienceLevel) nextErrors.experienceLevel = "Select your experience level.";
    if (!input.targetRole.trim()) nextErrors.targetRole = "Enter your target role.";
    if (input.availableTimePerWeek < 1 || input.availableTimePerWeek > 40) nextErrors.availableTimePerWeek = "Enter weekly hours from 1 to 40.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) { performance.mark("career.validation.guidance-committed"); return; }
    void onSubmit();
  }
  return (
    <form onSubmit={submit} noValidate>
      <h2>Build your roadmap</h2>
      <label>Current role<input ref={roleRef} aria-describedby={errors.role ? "role-error" : undefined} aria-invalid={Boolean(errors.role)} required value={input.role} onChange={(event) => onChange({ ...input, role: event.target.value })} /></label>{errors.role && <p id="role-error" role="alert">{errors.role}</p>}
      <label>Experience level<select ref={levelRef} aria-describedby={errors.experienceLevel ? "level-error" : undefined} aria-invalid={Boolean(errors.experienceLevel)} required value={input.experienceLevel} onChange={(event) => onChange({ ...input, experienceLevel: event.target.value })}><option value="">Select level</option><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label>{errors.experienceLevel && <p id="level-error" role="alert">{errors.experienceLevel}</p>}
      <label>Target role<input ref={targetRef} aria-describedby={errors.targetRole ? "target-error" : undefined} aria-invalid={Boolean(errors.targetRole)} required value={input.targetRole} onChange={(event) => onChange({ ...input, targetRole: event.target.value })} /></label>{errors.targetRole && <p id="target-error" role="alert">{errors.targetRole}</p>}
      <label>Hours available per week<input ref={hoursRef} aria-describedby={errors.availableTimePerWeek ? "hours-error" : undefined} aria-invalid={Boolean(errors.availableTimePerWeek)} required min={1} max={40} type="number" value={input.availableTimePerWeek || ""} onChange={(event) => onChange({ ...input, availableTimePerWeek: Number(event.target.value) })} /></label>{errors.availableTimePerWeek && <p id="hours-error" role="alert">{errors.availableTimePerWeek}</p>}
      <button disabled={persistence.blocksNavigation} type="submit">Create roadmap</button>
      <PersistenceStatus snapshot={persistence} />
    </form>
  );
}
