import { describe, expect, it } from "vitest";
import { toBrowserLearningSession, toBrowserProblem, toBrowserReviewAttempt, toBrowserReviewResult, toCoreReviewAnswer } from "../../src/contracts/learning.js";

describe("learning contract mapping", () => {
  it("preserves pinned versions, ordered steps, retirement, and lab state", () => {
    const result = toBrowserLearningSession({ id: "s", roadmap_id: "r", content_version: "v1", question_version: "q1", lab_reference_versions: ["lab@v1"], title: "T", objective: "O", estimated_minutes: 25, status: "in_progress", current_step_ordinal: 1, retirement: { status: "retired", security_critical: false, replacement_content_id: "new" }, steps: [{ id: "one", ordinal: 0, step_type: "reading", title: "Read", status: "completed" }, { id: "two", ordinal: 1, step_type: "lab", title: "Lab", status: "pending", lab_reference: { id: "lab", provider: "P", objective: "Try", prerequisites: [], estimated_minutes: 20, cost_status: "free", availability_status: "unavailable", destination_url: "https://example.test" } }] });
    expect(result).toMatchObject({ contentVersion: "v1", questionVersion: "q1", labReferenceVersions: ["lab@v1"], currentStepOrdinal: 1, retirement: { status: "retired", replacementContentId: "new" }, steps: [{ id: "one" }, { labReference: { availabilityStatus: "unavailable", costStatus: "free" } }] });
  });
  it("restores only safe submitted answers and never unanswered keys", () => {
    const result = toBrowserReviewAttempt({ id: "a", attempt_number: 1, question_snapshot_version: "q1", status: "in_progress", questions: [{ id: "q", ordinal: 0, prompt: "?", choices: { a: "A", b: "B" }, correct_answer_key: "a" }], answers: [], started_at: "now", score_percent: null, passed: null, submitted_at: null });
    expect(JSON.stringify(result)).not.toContain("correct_answer_key");
    expect(result).toMatchObject({ questionSnapshotVersion: "q1", scorePercent: null, passed: null });
  });
  it("maps answers, review outcomes, and stable problems exactly", () => {
    expect(toCoreReviewAnswer({ answerKey: "a" })).toEqual({ answer_key: "a" });
    expect(toBrowserReviewResult({ attempt_id: "a", score_percent: 75, passed: false, session_status: "retry_required", missed_question_ids: ["q2"], next_action: { kind: "retry_material" } })).toMatchObject({ missedQuestionIds: ["q2"], nextAction: { kind: "retry_material" } });
    expect(toBrowserProblem({ status: 429, code: "REVIEW_RETRY_RATE_LIMITED", retryable: true, correlation_id: "trace", field_errors: {} })).toMatchObject({ code: "REVIEW_RETRY_RATE_LIMITED", retryable: true, traceId: "trace" });
  });
});
