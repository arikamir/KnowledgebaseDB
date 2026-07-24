import { RoadmapForm } from "./RoadmapForm";
import { RoadmapResult } from "./RoadmapResult";
import { useRoadmap } from "./useRoadmap";
import { LearnerContextNav } from "../../components/LearnerContextNav";

export function RoadmapPage() {
  const roadmap = useRoadmap();
  const mock = import.meta.env.DEV && ((window.location.hostname === "127.0.0.1" && window.location.pathname === "/roadmaps") || new URLSearchParams(window.location.search).get("mockSession") === "1");
  if (mock) {
    return <><LearnerContextNav />
      <h1>Career roadmap</h1>
      <p className="roadmap-lede">Your 10-milestone path to shipping production-ready DevOps systems.</p>
      <section className="mock-roadmap" aria-labelledby="mock-roadmap-title">
        <div className="roadmap-summary"><div><span className="eyebrow">Current progress</span><h2 id="mock-roadmap-title">6 of 10 milestones complete</h2></div><span className="roadmap-percent">60%</span></div>
        <div className="focus-progress" aria-label="60 percent of roadmap complete"><span style={{ width: "60%" }} /></div>
        <ol className="roadmap-milestones">
          {[
            ["Linux and networking foundations", "passed", "🥇", 100, 95, ""], ["Version control workflows", "passed", "🥈", 100, 85, ""], ["Container delivery fluency", "passed", "🥉", 100, 72, "containers docker beginner tutorial"], ["Continuous integration", "passed", "🥈", 100, 88, ""], ["Cloud infrastructure basics", "passed", "🥇", 100, 97, ""], ["Observability and incident response", "passed", "🥉", 100, 79, "observability incident response tutorial"], ["Safe production deployment", "current", "", 50, null, ""], ["DevSecOps practices", "upcoming", "", 0, null, ""], ["Platform engineering patterns", "upcoming", "", 0, null, ""], ["End-to-end capstone", "upcoming", "", 0, null, ""],
          ].map(([title, status, medal, percent, score, videoQuery], index) => <li key={title} className={`roadmap-milestone roadmap-${status}`}><span className="roadmap-marker">{medal || (status === "current" ? "→" : index + 1)}</span><div className="roadmap-course"><h3>{title}</h3><p>{status === "passed" ? "Milestone passed" : status === "current" ? "In progress · Add a deployment approval gate and rollback path" : "Upcoming milestone"}</p><div className="course-progress-row"><div className="course-progress" aria-label={`${percent}% complete`}><span style={{ width: `${percent}%` }} /></div>{score != null && <span className="course-score" aria-label={`Passing score ${score}%`}>{score}%</span>}</div>{videoQuery && <a className="youtube-suggestion" href={`https://www.youtube.com/results?search_query=${encodeURIComponent(videoQuery)}`} target="_blank" rel="noreferrer">▶ Watch suggested videos</a>}</div></li>)}
        </ol>
      </section>
    </>;
  }
  return <><LearnerContextNav /><h1>Career roadmap</h1><RoadmapForm input={roadmap.input} onChange={roadmap.setInput} onSubmit={roadmap.submit} persistence={roadmap.snapshot} />{roadmap.result && <RoadmapResult result={roadmap.result} />}</>;
}
