import { Link, Route, Routes, useLocation } from "react-router-dom";
import { useCallback, useEffect, useRef, useState } from "react";
import { registeredRoutes } from "./route-registry";
import { SessionTimeoutDialog } from "../components/SessionTimeoutDialog";
import { ProfileProvider } from "./profile-context";
import { bffRequest } from "../bff/client";
import type { BrowserSession } from "../contracts/bff-api";
import { authenticationEpoch } from "./auth-epoch";

function Home() {
  return (
    <>
      <h1>DevOps Career Agent</h1>
      <p>Your learning workspace is ready.</p>
      <p role="status" aria-live="polite">Checking service compatibility</p>
    </>
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
      <div className="app-shell">
      <header><Link className="brand" to="/">DevOps Career Agent</Link></header>
      <nav aria-label="Primary"><Link to="/">Home</Link>{routes.map((route) => <Link key={route.id} to={route.path}>{route.navigationLabel}</Link>)}</nav>
      <main id="main-content" ref={main} tabIndex={-1}>
        <Routes>
          <Route path="/" element={<Home />} />
          {routes.map((route) => <Route key={route.id} path={route.path} element={route.element} />)}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
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
    </ProfileProvider>
  );
}
