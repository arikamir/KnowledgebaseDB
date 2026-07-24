import { useLayoutEffect } from "react";
import { LabReferenceCard } from "../labs/LabReferenceCard";
import type { GuidanceResultValue } from "./useGuidance";

export function GuidanceResult({ result }: { result: GuidanceResultValue }) {
  useLayoutEffect(() => { performance.mark("guidance.result.accessible-render-committed"); }, [result]);
  return <section aria-labelledby="guidance-result-title">
    <h2 id="guidance-result-title">Guidance for {result.resolvedTopic}</h2>
    {result.requestedTopic.trim().toLocaleLowerCase() !== result.resolvedTopic.toLocaleLowerCase() && <p>Requested topic: {result.requestedTopic}</p>}
    <p>{result.topicSummary}</p>
    <h3>Fit for your current level</h3><p>{result.currentLevelFit}</p>
    <h3>Practical next action</h3><p>{result.practicalNextAction}</p>
    {result.commonPitfalls.length > 0 && <><h3>Common pitfalls</h3><ul>{result.commonPitfalls.map((pitfall) => <li key={pitfall}>{pitfall}</li>)}</ul></>}
    {result.labReferences.length > 0 && <><h3>Optional labs</h3>{result.labReferences.map((lab) => <LabReferenceCard key={lab.id} lab={lab} />)}</>}
  </section>;
}
