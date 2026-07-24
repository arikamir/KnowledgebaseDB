import { useParams } from "react-router-dom";
import { useState } from "react";
import { PersistenceStatus } from "../../components/PersistenceStatus";
import { LabExperience } from "../labs/LabExperience";
import { SessionReview } from "../review/SessionReview";
import { CompletionPanel } from "./CompletionPanel";
import { LearningSession } from "./LearningSession";
import { useLearningSession } from "./useLearningSession";
import { LearnerContextNav } from "../../components/LearnerContextNav";

export function LearningPage() {
  const id = useParams().id ?? "";
  const state = useLearningSession(id);
  const mock = import.meta.env.DEV && ((window.location.hostname === "127.0.0.1" && window.location.pathname.startsWith("/learning/")) || new URLSearchParams(window.location.search).get("mockSession") === "1");
  const [mockStep, setMockStep] = useState(1);
  const [mockAnswer, setMockAnswer] = useState("");
  const [mockChecked, setMockChecked] = useState(false);
  const [mockComplete, setMockComplete] = useState(false);

  if (mock) {
    const titles = ["Read the release policy", "Configure the approval gate", "Verify the rollback path"];
    const content = ["A production deployment should require an explicit decision from someone who can assess risk.", "Create a protected production environment and require one reviewer before deployment.", "Trigger a controlled failure in staging and confirm the previous version is recoverable."];
    return <><LearnerContextNav /><section className="learning-mock" aria-labelledby="learning-mock-title">
      <div className="learning-context"><span className="eyebrow">Current topic · Safe production deployment</span><span className="learning-time">25 min</span></div>
      <h1 id="learning-mock-title">Protected delivery pipeline</h1>
      <p className="learning-objective">Add an approval gate and rollback path so production releases stay deliberate, observable, and safe.</p>
      <div className="learning-progress" aria-label={`Step ${mockStep} of 3`}><span style={{ width: `${(mockStep / 3) * 100}%` }} /></div>
      <p className="learning-step-count">Step {mockStep} of 3</p>
      {mockComplete ? <section className="learning-completion" aria-labelledby="learning-complete-title"><span className="completion-medal" aria-hidden="true">✓</span><h2 id="learning-complete-title">Learning milestone complete</h2><p>You demonstrated an approval gate and a verified rollback path.</p><div className="learning-evidence"><strong>Evidence captured</strong><span>Approval gate configured</span><span>Rollback path verified</span><span>Release decision documented</span></div><button type="button" onClick={() => setMockComplete(false)}>Review learning</button></section> : <div className="learning-layout"><ol className="learning-steps" aria-label="Learning steps">{titles.map((title, index) => <li key={title} className={index + 1 === mockStep ? "learning-step active" : index + 1 < mockStep ? "learning-step done" : "learning-step"}><span className="learning-step-marker">{index + 1 < mockStep ? "✓" : index + 1}</span><span>{title}</span></li>)}</ol><article className="learning-content"><span className="topic-status">{mockStep === 3 ? "Final check" : "In progress"}</span><h2>{mockStep === 1 ? "Why approval gates matter" : mockStep === 2 ? "Configure the approval gate" : "Verify the rollback path"}</h2><p>{content[mockStep - 1]}</p><div className="learning-callout"><strong>What good looks like</strong><span>{mockStep === 1 ? "You can explain who approves production and why." : mockStep === 2 ? "A release pauses until an approved reviewer continues it." : "A failed release returns to the last known-good version."}</span></div><div className="learning-check"><strong>Quick knowledge check</strong><label htmlFor="learning-answer">What should happen before a production release?</label><select id="learning-answer" value={mockAnswer} onChange={(event) => { setMockAnswer(event.target.value); setMockChecked(false); }}><option value="">Choose an answer</option><option value="approval">A reviewer approves the release</option><option value="skip">Skip review for speed</option></select>{mockChecked && <p className="learning-feedback" role="status">{mockAnswer === "approval" ? "Correct—this is the guardrail you just practiced." : "Not quite. Production releases should pause for explicit approval."}</p>}</div><button type="button" className="check-answer" disabled={!mockAnswer} onClick={() => setMockChecked(true)}>Check answer</button><button type="button" disabled={!mockChecked || mockAnswer !== "approval"} onClick={() => { if (mockStep === 3) setMockComplete(true); else { setMockStep((current) => current + 1); setMockAnswer(""); setMockChecked(false); } }}>{mockStep === 3 ? "Complete learning" : "Mark step complete"}</button></article></div>}
    </section></>;
  }
  if (!state.session) return <><h1>Focused learning</h1><p role="status">Loading your saved learning session…</p><PersistenceStatus snapshot={state.snapshot} /></>;
  const lab = state.session.steps.find((step) => step.stepType === "lab")?.labReference;
  return <><h1>Focused learning</h1><LearningSession session={state.session} onComplete={state.completeStep} />{lab && <LabExperience lab={lab} onReport={(reason) => state.reportLab(lab.id, reason)} onReturn={state.load} />}{!state.attempt && !state.completion && <button disabled={state.snapshot.state === "saving"} onClick={() => void state.beginReview()}>Begin review</button>}{state.attempt && !state.completion && <SessionReview attempt={state.attempt} feedback={state.feedback} onAnswer={state.answer} onSubmit={state.submitReview} />}{state.completion && <CompletionPanel result={state.completion} onRetry={state.retryReview} />}<PersistenceStatus snapshot={state.snapshot} />{state.problem && <p role="alert">{state.problem === "REVIEW_RETRY_RATE_LIMITED" ? "Try another review in 15 minutes." : "Your input is preserved. Try again."}</p>}</>;
}
