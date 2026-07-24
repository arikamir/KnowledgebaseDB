import { useState } from "react";
import { PersistenceMachine } from "../../app/persistence-state";
import { useProfile } from "../../app/profile-context";
import { submittedOperations } from "../../app/submitted-operation-registry";
import { bffRequest } from "../../bff/client";
import { GUIDANCE_CATALOG_VERSION } from "../../contracts/supported-guidance-topics";
import { safeTelemetry } from "../../telemetry/safe-telemetry";

export interface GuidanceLab {
  id: string; provider: string; objective: string; prerequisites: string[];
  estimatedMinutes: number; costStatus: "free" | "paid" | "subscription" | "unknown";
  destinationUrl: string; availabilityStatus: "active" | "unavailable" | "retired";
}

export interface GuidanceResultValue {
  requestedTopic: string; resolvedTopic: string; supported: true; topicSummary: string;
  currentLevelFit: string; practicalNextAction: string; labReferences: GuidanceLab[];
  suggestions: string[]; commonPitfalls: string[]; relatedTopics: string[]; notes: string[];
}

export interface GuidanceProblem {
  code: string; detail?: string | null; retryable?: boolean;
  fieldErrors?: Array<{ field: string; messages: string[] }>;
}

function problemFrom(error: unknown): GuidanceProblem {
  const problem = (error as { problem?: GuidanceProblem })?.problem;
  return problem ?? { code: error instanceof Error ? error.message : "CORE_UNAVAILABLE", retryable: true };
}

export function useGuidance() {
  const { profile, setProfile } = useProfile();
  const [topic, setTopic] = useState("");
  const [result, setResult] = useState<GuidanceResultValue | null>(null);
  const [problem, setProblem] = useState<GuidanceProblem | null>(null);
  const [persistence] = useState(() => new PersistenceMachine());
  const [snapshot, setSnapshot] = useState(persistence.snapshot);

  async function submit() {
    setProblem(null);
    const intent = JSON.stringify({ topic, profile });
    const key = submittedOperations.keyFor("create-guidance", intent);
    setSnapshot(persistence.begin());
    const resolution = await submittedOperations.submit("create-guidance", intent, key, () => bffRequest<GuidanceResultValue>("/bff/v1/guidance", {
      method: "POST",
      body: JSON.stringify({ topic, employeeProfile: profile }),
      headers: {
        "Content-Type": "application/json", "Idempotency-Key": key,
        "X-UI-Contract-Version": "1.0.0", "X-Guidance-Catalog-Version": GUIDANCE_CATALOG_VERSION,
      },
    }));
    if (resolution.state === "saved") {
      performance.mark("guidance.result.fetch-resolved");
      setResult(resolution.value); setSnapshot(persistence.succeed());
      safeTelemetry({ event: "guidance_success", catalog_version: GUIDANCE_CATALOG_VERSION, lab_count: resolution.value.labReferences.length });
    } else {
      const nextProblem = problemFrom(resolution.error);
      setProblem(nextProblem);
      setSnapshot(resolution.state === "save_unknown" ? persistence.uncertain() : persistence.fail());
      safeTelemetry({ event: "guidance_failure", code: nextProblem.code, retryable: Boolean(nextProblem.retryable) });
    }
  }

  return { profile, setProfile, topic, setTopic, result, problem, submit, snapshot };
}
