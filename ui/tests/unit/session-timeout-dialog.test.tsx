import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SessionTimeoutDialog } from "../../src/components/SessionTimeoutDialog";

describe("session timeout dialog", () => {
  it("offers extension only for an idle deadline within two minutes", () => {
    const now = Date.parse("2026-07-16T09:00:00Z");
    render(<SessionTimeoutDialog idleExpiresAt="2026-07-16T09:01:00Z" absoluteExpiresAt="2026-07-16T10:00:00Z" onContinue={async () => {}} onExpired={() => {}} now={() => now} />);
    expect(screen.getByRole("dialog")).toBeVisible();
    expect(screen.getByRole("button", { name: "Continue session" })).toBeVisible();
  });

  it("explains a nonextendable absolute deadline without an extension control", () => {
    const now = Date.parse("2026-07-16T09:00:00Z");
    render(<SessionTimeoutDialog idleExpiresAt="2026-07-16T10:00:00Z" absoluteExpiresAt="2026-07-16T09:01:00Z" onContinue={async () => {}} onExpired={() => {}} now={() => now} />);
    expect(screen.getByText(/cannot be extended/)).toBeVisible();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
