import { RoadmapForm } from "./RoadmapForm";
import { RoadmapResult } from "./RoadmapResult";
import { useRoadmap } from "./useRoadmap";

export function RoadmapPage() {
  const roadmap = useRoadmap();
  return <><h1>Career roadmap</h1><RoadmapForm input={roadmap.input} onChange={roadmap.setInput} onSubmit={roadmap.submit} persistence={roadmap.snapshot} />{roadmap.result && <RoadmapResult result={roadmap.result} />}</>;
}
