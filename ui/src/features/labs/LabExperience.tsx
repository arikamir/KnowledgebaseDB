import type { LabValue } from "../learning/useLearningSession";
import { useState } from "react";

export function LabExperience({ lab, onReport, onReturn }: { lab: LabValue; onReport: (reason: string) => Promise<void>; onReturn: () => Promise<void> }) {
  const [reportStatus, setReportStatus] = useState("");
  return <section aria-labelledby={`lab-${lab.id}`}><h3 id={`lab-${lab.id}`}>{lab.provider} lab</h3><p>{lab.objective}</p><p>Availability: {lab.availabilityStatus}</p><p>Cost: {lab.costStatus}</p><p>Estimated time: {lab.estimatedMinutes} minutes</p>{lab.availabilityStatus === "active" ? <a href={lab.destinationUrl} target="_blank" rel="noopener noreferrer" onClick={() => performance.mark("learning.required-clock.pause-external-lab")}>Open lab in a new tab</a> : <p>This lab cannot be opened.</p>}<button onClick={() => void onReturn()}>I returned from the lab</button><button onClick={() => void onReport("unavailable").then(() => setReportStatus("Report saved. Existing reports remain on record."))}>Report unavailable lab</button><p role="status">{reportStatus}</p><p>Opening or returning from a lab does not mark it complete.</p></section>;
}
