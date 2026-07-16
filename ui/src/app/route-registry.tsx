import type { ReactElement } from "react";

export interface AppRoute {
  id: string;
  path: string;
  navigationLabel: string;
  element: ReactElement;
}

const routes = new Map<string, AppRoute>();

export function registerRoute(route: AppRoute): () => void {
  if (routes.has(route.id) || [...routes.values()].some((current) => current.path === route.path)) {
    throw new Error("DUPLICATE_ROUTE");
  }
  routes.set(route.id, route);
  return () => { routes.delete(route.id); };
}

export function registeredRoutes(): readonly AppRoute[] {
  return [...routes.values()];
}
