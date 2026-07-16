import { useRef, useState, type FormEvent } from "react";
import type { EditableProfile } from "../../app/profile-context";
import type { PersistenceSnapshot } from "../../app/persistence-state";
import { PersistenceStatus } from "../../components/PersistenceStatus";
import { GUIDANCE_TOPICS } from "../../contracts/supported-guidance-topics";
import type { GuidanceProblem } from "./useGuidance";

interface Props {
  topic: string; onTopicChange: (value: string) => void;
  profile: EditableProfile; onProfileChange: (value: EditableProfile) => void;
  onSubmit: () => Promise<void>; persistence: PersistenceSnapshot; problem: GuidanceProblem | null;
}

export function GuidanceForm({ topic, onTopicChange, profile, onProfileChange, onSubmit, persistence, problem }: Props) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const topicRef = useRef<HTMLInputElement>(null);
  function submit(event: FormEvent) {
    event.preventDefault();
    performance.mark("guidance.validation.attempt");
    const next: Record<string, string> = {};
    if (!topic.trim()) next.topic = "Enter a guidance topic.";
    else if ([...topic].length > 128) next.topic = "Enter no more than 128 characters.";
    if (!profile.role.trim()) next.role = "Enter your current role.";
    if (!profile.experienceLevel) next.experienceLevel = "Select your experience level.";
    setErrors(next);
    if (Object.keys(next).length) {
      performance.mark("guidance.validation.guidance-committed");
      topicRef.current?.focus();
      return;
    }
    void onSubmit();
  }
  const serverTopicError = problem?.fieldErrors?.find((error) => error.field === "topic")?.messages[0];
  const topicError = errors.topic ?? serverTopicError;
  return <form onSubmit={submit} noValidate>
    <h2>Explore a skill</h2>
    {(Object.keys(errors).length > 0 || problem) && <div className="error-summary" role="alert" tabIndex={-1}><h3>Check your guidance request</h3><p>{problem?.detail ?? Object.values(errors)[0] ?? "Correct the highlighted field."}</p></div>}
    <label>Guidance topic
      <input ref={topicRef} list="guidance-topics" maxLength={128} required value={topic} aria-invalid={Boolean(topicError)} aria-describedby={topicError ? "guidance-topic-error" : undefined} onChange={(event) => onTopicChange(event.target.value)} />
    </label>
    <datalist id="guidance-topics">{GUIDANCE_TOPICS.filter((item) => item.status === "active").map((item) => <option key={item.id} value={item.name} />)}</datalist>
    {topicError && <p id="guidance-topic-error" role="alert">{topicError}</p>}
    <label>Current role<input required value={profile.role} aria-invalid={Boolean(errors.role)} aria-describedby={errors.role ? "guidance-role-error" : undefined} onChange={(event) => onProfileChange({ ...profile, role: event.target.value })} /></label>
    {errors.role && <p id="guidance-role-error" role="alert">{errors.role}</p>}
    <label>Experience level<select required value={profile.experienceLevel} aria-invalid={Boolean(errors.experienceLevel)} aria-describedby={errors.experienceLevel ? "guidance-level-error" : undefined} onChange={(event) => onProfileChange({ ...profile, experienceLevel: event.target.value })}><option value="">Select level</option><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label>
    {errors.experienceLevel && <p id="guidance-level-error" role="alert">{errors.experienceLevel}</p>}
    <label>Target role<input value={profile.targetRole} onChange={(event) => onProfileChange({ ...profile, targetRole: event.target.value })} /></label>
    <label>Hours available per week<input type="number" min={0} max={168} value={profile.availableTimePerWeek || ""} onChange={(event) => onProfileChange({ ...profile, availableTimePerWeek: Number(event.target.value) })} /></label>
    <button type="submit" disabled={persistence.state === "saving"}>{problem?.retryable ? "Retry guidance" : "Get guidance"}</button>
    <PersistenceStatus snapshot={persistence} />
  </form>;
}
