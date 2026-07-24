import { ProgressForm } from "./ProgressForm";
import { ProgressReview } from "./ProgressReview";
import { useProgress } from "./useProgress";
import { useState } from "react";
import { LearnerContextNav } from "../../components/LearnerContextNav";

export function ProgressPage() {
  const progress = useProgress();
  const mock = import.meta.env.DEV && ((window.location.hostname === "127.0.0.1" && window.location.pathname === "/progress") || new URLSearchParams(window.location.search).get("mockSession") === "1");
  const [checkedIn, setCheckedIn] = useState(false);
  if (mock) return <><LearnerContextNav /><section className="progress-mock" aria-labelledby="progress-mock-title">
    <p className="eyebrow">Roadmap check-in</p><h1 id="progress-mock-title">Your progress is moving forward</h1><p className="progress-lede">You have completed 6 of 10 milestones. Keep your attention on safe production deployment.</p>
    <div className="progress-score-card"><div><span className="eyebrow">Overall completion</span><strong>60%</strong></div><div className="focus-progress" aria-label="60 percent roadmap completion"><span style={{ width: "60%" }} /></div><span className="progress-caption">6 completed · 1 in progress · 3 upcoming</span></div>
    <div className="progress-grid"><section className="progress-panel"><h2>What you have achieved</h2><ul className="progress-achievements"><li><span>🥇</span><div><strong>Cloud infrastructure basics</strong><small>97% assessment score</small></div></li><li><span>🥈</span><div><strong>Continuous integration</strong><small>88% assessment score</small></div></li><li><span>🥉</span><div><strong>Observability and incident response</strong><small>79% assessment score</small></div></li></ul></section><section className="progress-panel progress-next"><span className="topic-status">Recommended next action</span><h2>Finish the deployment approval gate</h2><p>Complete the current learning steps, then verify the rollback path before taking the milestone exam.</p><a className="focus-link" href="/learning/session-1">Continue learning →</a></section></div>
    <section className="progress-checkin"><div><h2>{checkedIn ? "Check-in recorded" : "Ready to record your progress?"}</h2><p>{checkedIn ? "Your current focus and next action have been saved to the roadmap." : "A check-in keeps your roadmap recommendations aligned with what you have actually completed."}</p></div>{!checkedIn && <button type="button" onClick={() => setCheckedIn(true)}>Record check-in</button>}</section>
  </section></>;
  return <>
    <h1>Progress check-in</h1>
    {progress.notice && <p role="status">{progress.notice}</p>}
    <ProgressForm input={progress.input} onChange={progress.setInput} onSubmit={progress.submit} persistence={progress.snapshot} problem={progress.problem} />
    {progress.review && <ProgressReview review={progress.review} />}
  </>;
}
