import { useParams } from "react-router-dom";
import { PersistenceStatus } from "../../components/PersistenceStatus";
import { LabExperience } from "../labs/LabExperience";
import { SessionReview } from "../review/SessionReview";
import { CompletionPanel } from "./CompletionPanel";
import { LearningSession } from "./LearningSession";
import { useLearningSession } from "./useLearningSession";

export function LearningPage() {
  const id = useParams().id ?? ""; const state = useLearningSession(id);
  if (!state.session) return <><h1>Focused learning</h1><p role="status">Loading your saved learning session…</p><PersistenceStatus snapshot={state.snapshot} /></>;
  const lab = state.session.steps.find((step) => step.stepType === "lab")?.labReference;
  return <><h1>Focused learning</h1><LearningSession session={state.session} onComplete={state.completeStep} />{lab && <LabExperience lab={lab} onReport={(reason) => state.reportLab(lab.id, reason)} onReturn={state.load} />}{!state.attempt && !state.completion && <button disabled={state.snapshot.state === "saving"} onClick={() => void state.beginReview()}>Begin review</button>}{state.attempt && !state.completion && <SessionReview attempt={state.attempt} feedback={state.feedback} onAnswer={state.answer} onSubmit={state.submitReview} />}{state.completion && <CompletionPanel result={state.completion} onRetry={state.retryReview} />}<PersistenceStatus snapshot={state.snapshot} />{state.problem && <p role="alert">{state.problem === "REVIEW_RETRY_RATE_LIMITED" ? "Try another review in 15 minutes." : "Your input is preserved. Try again."}</p>}</>;
}
