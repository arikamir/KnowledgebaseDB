import { GuidanceForm } from "./GuidanceForm";
import { GuidanceResult } from "./GuidanceResult";
import { useGuidance } from "./useGuidance";
import { LearnerContextNav } from "../../components/LearnerContextNav";

export function GuidancePage() {
  const guidance = useGuidance();
  const mock = import.meta.env.DEV && ((window.location.hostname === "127.0.0.1" && window.location.pathname === "/guidance") || new URLSearchParams(window.location.search).get("mockSession") === "1");
  if (mock) return <><LearnerContextNav /><section className="guidance-mock" aria-labelledby="guidance-mock-title">
    <p className="eyebrow">Current topic · Safe production deployment</p>
    <h1 id="guidance-mock-title">Build a deployment approval gate</h1>
    <p className="guidance-lede">Turn your current milestone into a repeatable, low-risk release workflow.</p>
    <div className="guidance-meta"><span>Intermediate</span><span>~45 minutes</span><span>DevOps delivery</span></div>
    <div className="guidance-grid">
      <article className="guidance-panel guidance-panel-primary"><h2>Why this matters</h2><p>Approval gates make the safe path the easy path. They create a deliberate pause before production while keeping ownership and rollback decisions visible.</p><h2>Practical next action</h2><p className="guidance-action">Add a protected production environment to your pipeline and require one reviewer before deployment.</p><button type="button">Start practice</button></article>
      <aside className="guidance-panel"><h2>Keep in mind</h2><ul><li>Keep staging and production configuration separate.</li><li>Make rollback as easy as deploy.</li><li>Record who approved and what changed.</li></ul><h2>Suggested lab</h2><p>Protected delivery pipeline</p><span className="lab-meta">Hands-on · 20 minutes · Free</span></aside>
    </div>
  </section></>;
  return <><h1>Skill guidance</h1><GuidanceForm topic={guidance.topic} onTopicChange={guidance.setTopic} profile={guidance.profile} onProfileChange={guidance.setProfile} onSubmit={guidance.submit} persistence={guidance.snapshot} problem={guidance.problem} />{guidance.result && <GuidanceResult result={guidance.result} />}</>;
}
