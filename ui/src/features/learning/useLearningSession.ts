import { useCallback, useEffect, useState } from "react";
import { PersistenceMachine } from "../../app/persistence-state";
import { submittedOperations } from "../../app/submitted-operation-registry";
import { bffRequest } from "../../bff/client";

export interface LearningStepValue { id: string; ordinal: number; stepType: "reading" | "activity" | "lab" | "review"; title: string; status: "pending" | "completed"; labReference?: LabValue | null; }
export interface LabValue { id: string; provider: string; objective: string; prerequisites: string[]; estimatedMinutes: number; costStatus: string; availabilityStatus: "active" | "unavailable" | "retired"; destinationUrl: string; }
export interface LearningSessionValue { id: string; roadmapId: string; contentVersion: string; questionVersion: string; labReferenceVersions: string[]; title: string; objective: string; estimatedMinutes: number; status: string; currentStepOrdinal: number; steps: LearningStepValue[]; retirement: { status: string; securityCritical: boolean; resumeUntil?: string | null; replacementContentId?: string | null; replacementContentVersion?: string | null }; }
export interface QuestionValue { id: string; ordinal: number; prompt: string; choices: Record<string, string>; }
export interface ReviewAttemptValue { id: string; attemptNumber: number; status: "in_progress" | "submitted"; questions: QuestionValue[]; answers: Array<{ questionId: string; submittedAnswerKey: string; correct: boolean; explanation: string }>; scorePercent: number | null; passed: boolean | null; latest?: boolean; highest?: boolean; }

export function useLearningSession(resourceId: string) {
  const [session, setSession] = useState<LearningSessionValue | null>(null);
  const [attempt, setAttempt] = useState<ReviewAttemptValue | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [completion, setCompletion] = useState<Record<string, unknown> | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [persistence] = useState(() => new PersistenceMachine());
  const [snapshot, setSnapshot] = useState(persistence.snapshot);

  const mutate = useCallback(async <T,>(action: string, intent: object, path: `/bff/v1/${string}`, init: RequestInit): Promise<T | null> => {
    const digest = JSON.stringify(intent); const key = submittedOperations.keyFor(action, digest); setSnapshot(persistence.begin());
    const resolution = await submittedOperations.submit(action, digest, key, () => bffRequest<T>(path, { ...init, headers: { "Idempotency-Key": key, "X-UI-Contract-Version": "1.0.0", ...init.headers } }));
    if (resolution.state === "saved") { setSnapshot(persistence.succeed()); setProblem(null); return resolution.value; }
    setSnapshot(resolution.state === "save_unknown" ? persistence.uncertain() : persistence.fail());
    setProblem(((resolution.error as { problem?: { code?: string } })?.problem?.code) ?? "CORE_UNAVAILABLE"); return null;
  }, [persistence]);

  const load = useCallback(async () => {
    try { setSession(await bffRequest<LearningSessionValue>(`/bff/v1/learning-sessions/${resourceId}`)); }
    catch { const value = await mutate<LearningSessionValue>("start-learning", { resourceId }, `/bff/v1/learning-sessions/${resourceId}/start`, { method: "POST" }); if (value) setSession(value); }
  }, [mutate, resourceId]);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- initial authoritative BFF synchronization
  useEffect(() => { void load(); }, [load]);

  async function completeStep(stepId: string) { const value = await mutate<LearningSessionValue>("complete-step", { sessionId: session?.id, stepId }, `/bff/v1/learning-sessions/${session!.id}/steps/${stepId}/completion`, { method: "PUT" }); if (value) setSession(value); }
  async function beginReview() { const value = await mutate<ReviewAttemptValue>("start-review", { sessionId: session?.id }, `/bff/v1/learning-sessions/${session!.id}/review-attempts`, { method: "POST" }); if (value) setAttempt(value); }
  async function answer(questionId: string, answerKey: string) { const value = await mutate<{ correct: boolean; explanation: string }>("answer-review", { attemptId: attempt?.id, questionId, answerKey }, `/bff/v1/review-attempts/${attempt!.id}/answers/${questionId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answerKey }) }); if (value) { setFeedback(`${value.correct ? "Correct." : "Not quite."} ${value.explanation}`); performance.mark("learning.review.feedback-committed"); } }
  async function submitReview() { const value = await mutate<Record<string, unknown>>("submit-review", { attemptId: attempt?.id }, `/bff/v1/review-attempts/${attempt!.id}/submit`, { method: "POST" }); if (value) setCompletion(value); }
  async function reportLab(labId: string, reason: string) { await mutate("report-lab", { labId, reason }, `/bff/v1/lab-references/${labId}/reports`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason }) }); }
  return { session, attempt, feedback, completion, problem, snapshot, load, completeStep, beginReview, answer, submitReview, reportLab };
}
