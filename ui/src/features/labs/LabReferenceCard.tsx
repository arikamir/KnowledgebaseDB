import type { GuidanceLab } from "../guidance/useGuidance";

export function LabReferenceCard({ lab }: { lab: GuidanceLab }) {
  const state = lab.availabilityStatus;
  return <article className="lab-card">
    <h3>{lab.provider} lab</h3>
    <p>{lab.objective}</p>
    <p><strong>Availability:</strong> {state}</p>
    <p><strong>Cost:</strong> {lab.costStatus}</p>
    {state === "active" ? <a href={lab.destinationUrl} target="_blank" rel="noopener noreferrer">Open lab in a new tab</a> : <p>This lab cannot be opened right now.</p>}
    <p>Opening a lab does not mark it complete.</p>
  </article>;
}
