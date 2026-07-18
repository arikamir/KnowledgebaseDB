import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { App } from "../../src/app/App";

describe("App", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders the accessible application heading", () => {
    render(<MemoryRouter><App /></MemoryRouter>);
    expect(screen.getByRole("heading", { level: 1, name: "DevOps Career Agent" })).toBeVisible();
  });

  it("loads browser session expiry and refreshes it when continuing", async () => {
    const fetcher = vi.fn(() => Promise.resolve(new Response(JSON.stringify({
      authenticated: true,
      csrfToken: "opaque-csrf-token",
      idleExpiresAt: new Date(Date.now() + 60_000).toISOString(),
      absoluteExpiresAt: new Date(Date.now() + 8 * 60 * 60_000).toISOString(),
    }), { status: 200, headers: { "Content-Type": "application/json" } })));
    vi.stubGlobal("fetch", fetcher);

    render(<MemoryRouter><App /></MemoryRouter>);
    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByRole("button", { name: "Continue session" })).toBeVisible();
    await screen.getByRole("button", { name: "Continue session" }).click();
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(fetcher).toHaveBeenNthCalledWith(1, "/bff/v1/session", expect.objectContaining({ credentials: "same-origin" }));
  });
});
