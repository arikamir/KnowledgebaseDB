/* eslint-disable @typescript-eslint/no-explicit-any -- boundary mapper narrows generated JSON dynamically */
export function toBrowserLearningSession(value: Record<string, any>): Record<string, unknown> {
  return {
    id: value.id, roadmapId: value.roadmap_id, contentVersion: value.content_version,
    questionVersion: value.question_version, labReferenceVersions: value.lab_reference_versions ?? [],
    title: value.title, objective: value.objective, estimatedMinutes: value.estimated_minutes,
    status: value.status, currentStepOrdinal: value.current_step_ordinal,
    retirement: {
      status: value.retirement?.status ?? "published",
      securityCritical: value.retirement?.security_critical ?? false,
      resumeUntil: value.retirement?.resume_until ?? null,
      replacementContentId: value.retirement?.replacement_content_id ?? null,
      replacementContentVersion: value.retirement?.replacement_content_version ?? null,
    },
    steps: (value.steps ?? []).map((step: Record<string, any>) => ({ id: step.id, ordinal: step.ordinal, stepType: step.step_type, title: step.title, status: step.status, labReference: step.lab_reference ? toBrowserLab(step.lab_reference) : null })),
  };
}

function toBrowserLab(lab: Record<string, any>): Record<string, unknown> {
  return { id: lab.id, provider: lab.provider, objective: lab.objective, prerequisites: lab.prerequisites ?? [], estimatedMinutes: lab.estimated_minutes, costStatus: lab.cost_status, availabilityStatus: lab.availability_status, destinationUrl: lab.destination_url };
}

function toBrowserAnswer(answer: Record<string, any>): Record<string, unknown> {
  return { questionId: answer.question_id, submittedAnswerKey: answer.submitted_answer_key, correct: answer.correct, explanation: answer.explanation, answeredAt: answer.answered_at };
}

export function toBrowserReviewAttempt(value: Record<string, any>): Record<string, unknown> {
  return {
    id: value.id, attemptNumber: value.attempt_number, questionSnapshotVersion: value.question_snapshot_version,
    status: value.status, startedAt: value.started_at, scorePercent: value.score_percent,
    passed: value.passed, submittedAt: value.submitted_at, latest: value.latest, highest: value.highest,
    questions: (value.questions ?? []).map((question: Record<string, any>) => ({ id: question.id, ordinal: question.ordinal, prompt: question.prompt, choices: question.choices })),
    answers: (value.answers ?? []).map(toBrowserAnswer),
  };
}

export function toCoreReviewAnswer(value: { answerKey: string }): object { return { answer_key: value.answerKey }; }
export function toCoreLabReport(value: { reason: string; comment?: string | null }): object { return { reason: value.reason, comment: value.comment ?? null }; }

export function toBrowserReviewFeedback(value: Record<string, any>): Record<string, unknown> { return toBrowserAnswer(value); }

export function toBrowserReviewResult(value: Record<string, any>): Record<string, unknown> {
  return { attemptId: value.attempt_id, scorePercent: value.score_percent, passed: value.passed, sessionStatus: value.session_status, missedQuestionIds: value.missed_question_ids ?? [], nextAction: value.next_action };
}

export function toBrowserProblem(value: Record<string, any>): Record<string, unknown> {
  return { type: value.type ?? "about:blank", title: value.title ?? "Learning operation failed", status: value.status ?? 500, code: value.code ?? "CORE_UNAVAILABLE", detail: value.detail ?? null, traceId: value.correlation_id ?? "unknown", retryable: value.retryable ?? false, fieldErrors: Object.entries(value.field_errors ?? {}).map(([field, messages]) => ({ field, messages })) };
}
