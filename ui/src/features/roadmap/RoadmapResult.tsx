import { useLayoutEffect } from "react";
import type { RoadmapResultValue } from "./useRoadmap";

export function RoadmapResult({ result }: { result: RoadmapResultValue }) {
  useLayoutEffect(() => { performance.mark("career.result.accessible-render-committed"); }, [result]);
  if (result.status === "needsMoreInfo") {
    return <section aria-labelledby="clarification-title"><h2 id="clarification-title">A little more information is needed</h2><ul>{result.clarifyingQuestions?.map((question) => <li key={question.id ?? question.prompt}>{question.prompt}</li>)}</ul></section>;
  }
  return <section aria-labelledby="roadmap-title"><h2 id="roadmap-title">Your career roadmap</h2><ol>{result.roadmap?.milestones.map((milestone) => <li key={milestone.id ?? milestone.title}><h3>{milestone.title}</h3><p>{milestone.concreteNextAction ?? milestone.concrete_next_action}</p></li>)}</ol></section>;
}
