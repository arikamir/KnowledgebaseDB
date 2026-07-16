import { useState } from "react";
import type { ReviewAttemptValue } from "../learning/useLearningSession";

export function SessionReview({ attempt, feedback, onAnswer, onSubmit }: { attempt: ReviewAttemptValue; feedback: string | null; onAnswer: (questionId: string, key: string) => Promise<void>; onSubmit: () => Promise<void> }) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  return <section aria-labelledby="review-title"><h2 id="review-title">Knowledge review</h2><p>Attempt {attempt.attemptNumber}{attempt.latest ? " — latest" : ""}{attempt.highest ? " — highest score" : ""}</p>{attempt.questions.map((question) => <fieldset key={question.id}><legend>{question.prompt}</legend>{Object.entries(question.choices).map(([key, label]) => <label key={key}><input type="radio" name={question.id} value={key} checked={answers[question.id] === key} onChange={() => setAnswers({ ...answers, [question.id]: key })} />{label}</label>)}<button disabled={!answers[question.id]} onClick={() => void onAnswer(question.id, answers[question.id])}>Check answer</button></fieldset>)}<p role="status" aria-live="polite">{feedback}</p><button onClick={() => void onSubmit()}>Submit full review</button></section>;
}
