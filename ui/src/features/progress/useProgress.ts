import { useCallback, useEffect, useState } from "react";
import { authenticationEpoch } from "../../app/auth-epoch";
import { PersistenceMachine } from "../../app/persistence-state";
import { submittedOperations } from "../../app/submitted-operation-registry";
import { bffRequest } from "../../bff/client";
import type { BrowserSession, ProblemDetails, ProgressCheckInRequest, ProgressReview } from "../../contracts/bff-api";
import type { ProgressInput } from "./ProgressForm";

const EMPTY: ProgressInput = { roadmapId: "", notes: "", completedSteps: "", completedMilestoneKeys: "", newGoals: "" };
let memory: { epoch: number; input: ProgressInput; review: ProgressReview | null } | null = null;

function list(value: string): string[] {
  return value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean);
}

function problemFrom(error: unknown): ProblemDetails {
  const problem = (error as { problem?: ProblemDetails })?.problem;
  return problem ?? { type: "about:blank", title: "Progress operation failed", status: 503, code: error instanceof Error ? error.message : "CORE_UNAVAILABLE", retryable: true };
}

async function latestReview(roadmapId: string): Promise<ProgressReview | null> {
  try {
    return await bffRequest<ProgressReview>(`/bff/v1/progress/reviews?roadmapId=${encodeURIComponent(roadmapId)}`);
  } catch (error) {
    if (problemFrom(error).code === "PROGRESS_REVIEW_NOT_FOUND") return null;
    throw error;
  }
}

export function useProgress() {
  const epoch = authenticationEpoch.capture();
  const currentMemory = memory?.epoch === epoch ? memory : null;
  const urlRoadmap = typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("roadmapId") ?? "";
  const initial = currentMemory?.input ?? { ...EMPTY, roadmapId: urlRoadmap };
  const [input, setInputState] = useState<ProgressInput>(initial);
  const [review, setReview] = useState<ProgressReview | null>(currentMemory?.review ?? null);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [persistence] = useState(() => new PersistenceMachine());
  const [snapshot, setSnapshot] = useState(persistence.snapshot);
  const hasMemoryReview = Boolean(currentMemory?.review);
  const memoryRoadmapId = currentMemory?.review?.roadmapId ?? "";

  const setInput = useCallback((value: ProgressInput) => {
    setInputState(value); setProblem(null); setSnapshot(persistence.reset());
    memory = { epoch: authenticationEpoch.capture(), input: value, review };
  }, [persistence, review]);

  const reloadAuthoritative = useCallback(async (roadmapId: string, message: string) => {
    await bffRequest<unknown>(`/bff/v1/roadmaps/${encodeURIComponent(roadmapId)}`);
    const restored = await latestReview(roadmapId);
    setReview(restored); setNotice(message);
    memory = { epoch: authenticationEpoch.capture(), input: { ...input, roadmapId }, review: restored };
    return restored;
  }, [input]);

  useEffect(() => {
    if (!urlRoadmap || hasMemoryReview) return;
    const timeout = window.setTimeout(() => {
      void reloadAuthoritative(urlRoadmap, "Unsaved browser input was discarded; authoritative saved state was reloaded.")
        .then((restored) => { if (restored) setSnapshot(persistence.succeed()); })
        .catch((error) => setProblem(problemFrom(error)));
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [hasMemoryReview, persistence, reloadAuthoritative, urlRoadmap]);

  useEffect(() => {
    if (memoryRoadmapId && !urlRoadmap) {
      window.history.replaceState(null, "", `/progress?roadmapId=${encodeURIComponent(memoryRoadmapId)}`);
    }
  }, [memoryRoadmapId, urlRoadmap]);

  async function submit() {
    setProblem(null); setNotice(null);
    const request: ProgressCheckInRequest = {
      roadmapId: input.roadmapId.trim(), notes: input.notes,
      completedSteps: list(input.completedSteps), completedMilestoneKeys: list(input.completedMilestoneKeys), newGoals: list(input.newGoals),
    };
    const intent = JSON.stringify(request);
    const key = submittedOperations.keyFor("create-progress", intent);
    setSnapshot(persistence.begin());
    const resolution = await submittedOperations.submit("create-progress", intent, key, async () => {
      const session = await bffRequest<BrowserSession>("/bff/v1/session");
      if (!session.authenticated || !session.csrfToken) throw new Error("SESSION_NOT_ACTIVE");
      return bffRequest<ProgressReview>("/bff/v1/progress/check-ins", {
        method: "POST", body: JSON.stringify(request),
        headers: { "Content-Type": "application/json", "Idempotency-Key": key, "X-UI-Contract-Version": "1.0.0", "X-CSRF-Token": session.csrfToken },
      });
    });
    if (resolution.state === "saved") {
      performance.mark("progress.result.fetch-resolved");
      setReview(resolution.value); setSnapshot(persistence.succeed());
      memory = { epoch: authenticationEpoch.capture(), input, review: resolution.value };
      window.history.replaceState(null, "", `/progress?roadmapId=${encodeURIComponent(input.roadmapId)}`);
      return;
    }
    const nextProblem = problemFrom(resolution.error); setProblem(nextProblem);
    setSnapshot(resolution.state === "save_unknown" ? persistence.uncertain() : persistence.fail());
    if (nextProblem.code === "ROADMAP_VERSION_CONFLICT") {
      try {
        await reloadAuthoritative(input.roadmapId, "The roadmap changed. Authoritative progress was reloaded; review your preserved notes and submit again.");
      } catch (error) { setProblem(problemFrom(error)); }
    }
  }

  return { input, setInput, review, problem, notice, snapshot, submit };
}
