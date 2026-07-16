import { useState } from "react";
import { bffRequest } from "../../bff/client";
import { PersistenceMachine } from "../../app/persistence-state";
import { submittedOperations } from "../../app/submitted-operation-registry";

export interface RoadmapInput {
  role: string; experienceLevel: string; targetRole: string; availableTimePerWeek: number;
}
export interface RoadmapResultValue {
  status: "ready" | "needsMoreInfo";
  roadmap?: { id: string; goal_summary?: string; goalSummary?: string; milestones: Array<{ id?: string; title: string; concrete_next_action?: string; concreteNextAction?: string }> };
  clarifyingQuestions?: Array<{ id?: string; prompt: string; why_it_matters?: string; whyItMatters?: string }>;
}

export function useRoadmap() {
  const [result, setResult] = useState<RoadmapResultValue | null>(null);
  const [input, setInput] = useState<RoadmapInput>({ role: "", experienceLevel: "", targetRole: "", availableTimePerWeek: 0 });
  const [persistence] = useState(() => new PersistenceMachine());
  const [snapshot, setSnapshot] = useState(persistence.snapshot);

  async function submit() {
    const intent = JSON.stringify(input);
    const key = submittedOperations.keyFor("create-roadmap", intent);
    setSnapshot(persistence.begin());
    const resolution = await submittedOperations.submit("create-roadmap", intent, key, () => bffRequest<RoadmapResultValue>("/bff/v1/roadmaps", {
      method: "POST", body: JSON.stringify({ employeeProfile: input }),
      headers: { "Content-Type": "application/json", "Idempotency-Key": key, "X-UI-Contract-Version": "1.0.0" },
    }));
    if (resolution.state === "saved") {
      if (!resolution.value || !["ready", "needsMoreInfo"].includes(resolution.value.status)) throw new Error("BFF_RESPONSE_INVALID");
      performance.mark("career.result.fetch-resolved");
      setResult(resolution.value); setSnapshot(persistence.succeed());
    }
    else if (resolution.state === "save_unknown") setSnapshot(persistence.uncertain());
    else setSnapshot(persistence.fail());
  }

  return { input, setInput, result, submit, snapshot };
}
