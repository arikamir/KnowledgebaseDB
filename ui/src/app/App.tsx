import { Link, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useRef } from "react";
import { registeredRoutes } from "./route-registry";
import { SessionTimeoutDialog } from "../components/SessionTimeoutDialog";

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
  const routes = registeredRoutes();
  useEffect(() => { main.current?.focus(); }, [location.pathname]);
  return (
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
      <SessionTimeoutDialog onContinue={async () => {}} onExpired={() => {}} />
    </div>
  );
}
