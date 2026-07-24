import { Link, Route, Routes, useLocation } from "react-router-dom";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { registeredRoutes } from "./route-registry";
import { SessionTimeoutDialog } from "../components/SessionTimeoutDialog";
import { ProfileProvider, useProfile } from "./profile-context";
import { bffRequest } from "../bff/client";
import type { BrowserSession } from "../contracts/bff-api";
import { GUIDANCE_CATALOG_VERSION } from "../contracts/supported-guidance-topics";
import { authenticationEpoch } from "./auth-epoch";
import { LearnerStateProvider, useLearnerState } from "./learner-state-context";
import { fetchLearnerSnapshot } from "./learner-state-client";
import { LearnerContextNav } from "../components/LearnerContextNav";

function LearnerBootstrap({ authenticated }: { authenticated: boolean }) {
  const { dispatch, invalidate } = useLearnerState();
  useEffect(() => {
    if (!authenticated) { invalidate(); return; }
    // Home owns its existing roadmap bootstrap; avoid a duplicate request while
    // preserving the shared snapshot for secondary routes and mock mode.
    if (window.location.pathname === "/" && window.location.hostname !== "127.0.0.1") return;
    let cancelled = false;
    void fetchLearnerSnapshot().then((snapshot) => { if (!cancelled) dispatch({ type: "snapshot", snapshot }); });
    return () => { cancelled = true; };
  }, [authenticated, dispatch, invalidate]);
  return null;
}

type RoadmapSnapshot = {
  id: string;
  goal_summary?: string;
  goalSummary?: string;
  milestones?: Array<{ id?: string; title: string; concrete_next_action?: string; concreteNextAction?: string; completionState?: string; status?: string; progressPercent?: number; scorePercent?: number; score?: number }>;
};

type HomeGuidanceResult = {
  resolvedTopic?: string;
  topicSummary?: string;
  practicalNextAction?: string;
  suggestions?: string[];
  commonPitfalls?: string[];
};

function Home({ authenticated }: { authenticated: boolean }) {
  const { profile } = useProfile();
  const [draft, setDraft] = useState("");
  const [roadmap, setRoadmap] = useState<RoadmapSnapshot | null>(null);
  const [guidance, setGuidance] = useState<HomeGuidanceResult | null>(null);
  const [guidanceError, setGuidanceError] = useState<string | null>(null);
  const [guidancePending, setGuidancePending] = useState(false);

  useEffect(() => {
    if (!authenticated) return;
    if (import.meta.env.DEV && ((window.location.hostname === "127.0.0.1" && window.location.pathname === "/") || new URLSearchParams(window.location.search).get("mockSession") === "1")) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- deterministic development fixture
      setRoadmap({ id: "mock-roadmap", goal_summary: "Become confident shipping production-ready DevOps systems", milestones: [
        { id: "linux", title: "Linux and networking foundations", concreteNextAction: "Complete the command-line and TCP/IP practice lab", completionState: "completed", scorePercent: 95 },
        { id: "git", title: "Version control workflows", concreteNextAction: "Finish the branching and review exercise", completionState: "completed", scorePercent: 85 },
        { id: "containers", title: "Container delivery fluency", concreteNextAction: "Containerize a small service and publish it to a registry", completionState: "completed", scorePercent: 72 },
        { id: "ci", title: "Continuous integration", concreteNextAction: "Add automated tests to a CI pipeline", completionState: "completed", scorePercent: 88 },
        { id: "cloud", title: "Cloud infrastructure basics", concreteNextAction: "Provision a least-privilege cloud environment", completionState: "completed", scorePercent: 97 },
        { id: "observability", title: "Observability and incident response", concreteNextAction: "Trace a failed deployment from alert to root cause", completionState: "completed", scorePercent: 79 },
        { id: "deployment", title: "Safe production deployment", concreteNextAction: "Add a deployment approval gate and rollback path", completionState: "in_progress", progressPercent: 50 },
        { id: "security", title: "DevSecOps practices", concreteNextAction: "Scan dependencies and remediate a critical finding", completionState: "pending" },
        { id: "platform", title: "Platform engineering patterns", concreteNextAction: "Create a reusable service template", completionState: "pending" },
        { id: "capstone", title: "End-to-end capstone", concreteNextAction: "Ship and present a production-ready service", completionState: "pending" },
      ] });
      return;
    }
    const timeout = window.setTimeout(() => {
      void bffRequest<RoadmapSnapshot[]>("/bff/v1/roadmaps").then((items) => setRoadmap(items[0] ?? null)).catch(() => setRoadmap(null));
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [authenticated]);

  const submitPrompt = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const prompt = draft.trim();
    if (!prompt) return;
    setGuidanceError(null);
    setGuidancePending(true);
    try {
      const topic = roadmap?.milestones?.find((item) => item.completionState === "in_progress" || item.status === "in_progress")?.title ?? "DevOps career guidance";
      const result = await bffRequest<HomeGuidanceResult>("/bff/v1/guidance", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
          "X-UI-Contract-Version": "1.0.0",
          "X-Guidance-Catalog-Version": GUIDANCE_CATALOG_VERSION,
        },
        body: JSON.stringify({ topic, employeeProfile: profile, requestText: prompt }),
      });
      setGuidance(result);
      setDraft("");
    } catch {
      setGuidanceError("Guidance is temporarily unavailable. Your question is still here; try again.");
    } finally {
      setGuidancePending(false);
    }
  };

  return (
    <section className="chat-page" aria-labelledby="chat-title">
      <h1 id="chat-title" className="sr-only">Roadmap progress</h1>
      {authenticated && <LearnerContextNav />}

      {authenticated && roadmap && (
        <section className="focus-card current-topic-card" aria-labelledby="focus-title">
          {(() => {
            const topic = roadmap.milestones?.find((item) => item.completionState === "in_progress" || item.status === "in_progress") ?? roadmap.milestones?.[0];
            if (!topic) return null;
            const topics = roadmap.milestones ?? [];
            const currentIndex = Math.max(0, topics.indexOf(topic));
            const coursePercent = Math.round((currentIndex / Math.max(topics.length - 1, 1)) * 100);
            return <div className="topic-item topic-current">
              <span className="topic-number" aria-hidden="true">→</span>
              <div className="topic-content"><span className="topic-status">Current topic</span><h2 id="focus-title">{topic.title}</h2><div className="milestone-track" role="img" aria-label={`Milestone ${currentIndex + 1} of ${topics.length}`}><span className="milestone-track-fill" style={{ width: `${coursePercent}%` }} />{topics.map((milestone, index) => { const complete = index < currentIndex || milestone.completionState === "completed" || milestone.status === "completed"; const score = milestone.scorePercent ?? milestone.score; const medal = score == null ? "" : score >= 90 ? "🥇" : score >= 80 ? "🥈" : "🥉"; const achievement = score == null ? "completed" : `${medal} ${score >= 90 ? "gold" : score >= 80 ? "silver" : "bronze"} achievement`; return <span key={milestone.id ?? milestone.title} title={score != null ? `${achievement} · ${milestone.title}` : milestone.title} className={`milestone-dot ${complete ? "milestone-complete" : ""} ${index === currentIndex ? "milestone-current" : ""} ${medal ? "milestone-medal" : ""}`} style={{ left: `${topics.length === 1 ? 0 : (index / (topics.length - 1)) * 100}%` }}>{medal}<span className="sr-only">{milestone.title}, {achievement}</span></span>; })}</div><p className="milestone-caption">Milestone {currentIndex + 1} of {topics.length}</p><p>{topic.concreteNextAction ?? topic.concrete_next_action}</p><Link className="focus-link" to="/roadmaps">View full roadmap</Link></div>
            </div>;
          })()}
        </section>
      )}

      {guidance && <section className="guidance-response" aria-live="polite" aria-labelledby="home-guidance-title">
        <h2 id="home-guidance-title">{guidance.resolvedTopic ?? "Career guidance"}</h2>
        {guidance.topicSummary && <p>{guidance.topicSummary}</p>}
        {guidance.practicalNextAction && <><h3>Practical next action</h3><p>{guidance.practicalNextAction}</p></>}
        {(guidance.suggestions?.length ?? 0) > 0 && <><h3>Suggestions</h3><ul>{guidance.suggestions?.map((item) => <li key={item}>{item}</li>)}</ul></>}
        {(guidance.commonPitfalls?.length ?? 0) > 0 && <><h3>Common pitfalls</h3><ul>{guidance.commonPitfalls?.map((item) => <li key={item}>{item}</li>)}</ul></>}
      </section>}
      {guidanceError && <p className="form-error" role="alert">{guidanceError}</p>}

      <form className="chat-composer" onSubmit={submitPrompt}>
        <label htmlFor="career-prompt" className="sr-only">Message the Career Agent</label>
        <textarea
          id="career-prompt"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask a follow-up about your current roadmap..."
          rows={1}
        />
        <button type="submit" aria-label="Send message" disabled={!draft.trim() || guidancePending}>{guidancePending ? "…" : "↑"}</button>
      </form>
      {guidancePending && <p className="composer-status" role="status" aria-live="polite">Preparing guidance…</p>}
      <p className="composer-hint">Career guidance is an early preview. Do not share sensitive information.</p>
      <p className="compatibility-status" role="status" aria-live="polite">Checking service compatibility</p>
    </section>
  );
}

function NotFound() { return <><h1>Page not found</h1><p>The requested learning page is not available.</p></>; }

export function App() {
  const location = useLocation();
  const main = useRef<HTMLElement>(null);
  const [session, setSession] = useState<BrowserSession | null>(null);
  const routes = registeredRoutes();
  useEffect(() => { main.current?.focus(); }, [location.pathname]);

  const refreshSession = useCallback(async () => {
    if (import.meta.env.DEV && ((window.location.hostname === "127.0.0.1" && window.location.pathname === "/") || new URLSearchParams(window.location.search).get("mockSession") === "1")) {
      const expiresAt = new Date(Date.now() + 60 * 60 * 1000).toISOString();
      const mockSession: BrowserSession = {
        authenticated: true,
        employee: { displayName: "Alex Morgan" },
        csrfToken: "dev-only-mock-token",
        idleExpiresAt: expiresAt,
        absoluteExpiresAt: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
      };
      setSession(mockSession);
      return mockSession;
    }
    try {
      const current = await bffRequest<BrowserSession>("/bff/v1/session");
      setSession(current.authenticated ? current : null);
      return current;
    } catch {
      // A transient session-store failure must not clear a valid session or
      // manufacture a sign-out. A later user action or protected request retries.
      return null;
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => { void refreshSession(); }, 0);
    return () => {
      window.clearTimeout(initial);
    };
  }, [refreshSession]);

  const expireSession = useCallback(() => {
    authenticationEpoch.invalidate();
    setSession(null);
    const returnTo = `${window.location.pathname}${window.location.search}`;
    window.location.assign(`/bff/v1/auth/login?return_to=${encodeURIComponent(returnTo)}`);
  }, []);

  return (
    <ProfileProvider>
      <LearnerStateProvider>
      <LearnerBootstrap authenticated={Boolean(session)} />
      <div className="app-shell">
      <header className="app-header">
        <Link className="brand" to="/" aria-label="DevOps Career Agent"><span className="brand-mark" aria-hidden="true">✦</span> DevOps Career Agent</Link>
        {session && (
          <nav aria-label="Primary">{routes.map((route) => <Link key={route.id} to={route.path}>{route.navigationLabel}</Link>)}</nav>
        )}
        {!session && <a className="login-button" href="/bff/v1/auth/login">Log in</a>}
        {session && <span className="user-chip" aria-label={`Signed in as ${session.employee?.displayName ?? "user"}`}><span className="user-chip-avatar" aria-hidden="true">{(session.employee?.displayName ?? "U").charAt(0)}</span>{session.employee?.displayName ?? "Signed in"}</span>}
      </header>
      <main id="main-content" ref={main} tabIndex={-1}>
        <Routes>
          <Route path="/" element={<Home authenticated={Boolean(session)} />} />
          {routes.map((route) => <Route key={route.id} path={route.path} element={route.element} />)}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="app-footer">
        <div className="footer-inner">
          <div>
            <Link className="footer-brand" to="/"><span className="brand-mark" aria-hidden="true">✦</span> DevOps Career Agent</Link>
            <p className="footer-tagline">Practical guidance for your next professional move.</p>
          </div>
          <div className="footer-column">
            <h2>Explore</h2>
            <Link to="/">Home</Link>
            <Link to="/roadmaps">Career roadmaps</Link>
            <Link to="/guidance">Guidance</Link>
          </div>
          <div className="footer-column">
            <h2>Connect</h2>
            <a href="mailto:info@amarel.net">info@amarel.net</a>
            <a href="https://www.amarel.net" target="_blank" rel="noreferrer">amarel.net</a>
            <div className="footer-socials" aria-label="Social links">
              <a href="https://www.linkedin.com/company/amarel/" target="_blank" rel="noreferrer">LinkedIn</a>
              <a href="https://www.facebook.com/Amarel.LTD" target="_blank" rel="noreferrer">Facebook</a>
            </div>
          </div>
        </div>
        <div className="footer-bottom"><span>© {new Date().getFullYear()} DevOps Career Agent</span><span>Built for learning and career growth</span></div>
      </footer>
      <SessionTimeoutDialog
        idleExpiresAt={session?.idleExpiresAt}
        absoluteExpiresAt={session?.absoluteExpiresAt}
        onContinue={async () => {
          const current = await refreshSession();
          if (current && !current.authenticated) expireSession();
        }}
        onExpired={expireSession}
      />
      </div>
      </LearnerStateProvider>
    </ProfileProvider>
  );
}
