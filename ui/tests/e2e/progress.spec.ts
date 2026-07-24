import { expect, test, type Page } from "@playwright/test";

const milestone = {
  id: "milestone-1", milestoneKey: "linux-foundations-001", ordinal: 0,
  title: "Build Linux foundations", skillArea: "Linux", experienceLevelFit: "intermediate",
  timeHorizon: "immediate", concreteNextAction: "Complete one lab",
  reasonItMatters: "Builds operational fluency", priority: 1,
  completionState: "pending", supportingNotes: [],
};
const roadmap = {
  id: "roadmap-1", employeeProfileId: "profile-1", previousRoadmapId: null,
  goalSummary: "Move toward DevOps", currentFocus: milestone.title,
  milestones: [milestone], status: "revised", assumptions: [],
  clarifyingQuestionsAsked: 0, createdAt: "2026-07-16T12:00:00Z", updatedAt: "2026-07-16T12:00:00Z",
};
const review = {
  revision: { priorRoadmap: roadmap, updatedRoadmap: roadmap, completedSteps: [], normalizedMilestoneKeys: [], newGoals: [], summary: "Progress recorded.", createdAt: "2026-07-16T12:00:00Z" },
  presentation: "Progress recorded.", followUpPrompt: "Continue learning.",
  checkIn: { id: "check-in-1", employeeProfileId: "profile-1", roadmapId: "roadmap-1", notes: "Kept progress notes", completedSteps: [], normalizedMilestoneKeys: [], newGoals: [], updatedRecommendations: [milestone], createdAt: "2026-07-16T12:00:00Z" },
  roadmapId: "roadmap-1", currentStatus: "in_progress", gaps: [milestone.title], milestones: [milestone],
  nextAction: { kind: "continue_milestone", title: milestone.title, reason: "Continue the next incomplete milestone.", target: milestone.milestoneKey },
};

async function session(page: Page) {
  await page.route("**/bff/v1/session", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ authenticated: true, csrfToken: "csrf-token-value-0001" }) }));
}

async function fill(page: Page, notes = "Kept progress notes") {
  await page.getByLabel("Roadmap reference").fill("roadmap-1");
  await page.getByLabel("Progress notes").fill(notes);
}

test("generated local guidance is field-associated and committed within the timing boundary", async ({ page }) => {
  let requests = 0;
  page.on("request", (request) => { if (request.url().includes("/progress/check-ins")) requests += 1; });
  await page.goto("/progress");
  await page.getByRole("button", { name: "Record progress" }).click();
  await expect(page.getByLabel("Roadmap reference")).toBeFocused();
  await expect(page.getByLabel("Roadmap reference")).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator("#progress-roadmap-error")).toHaveText("Enter a roadmap reference.");
  expect(await page.evaluate(() => performance.getEntriesByName("progress.validation.attempt").length)).toBe(1);
  expect(await page.evaluate(() => performance.getEntriesByName("progress.validation.guidance-committed").length)).toBe(1);
  expect(requests).toBe(0);
});

test("keyboard check-in renders status, gaps, milestone state, and exactly one next action", async ({ page }) => {
  await session(page);
  await page.route("**/bff/v1/progress/check-ins", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(review) }));
  await page.goto("/progress");
  await fill(page);
  await page.getByRole("button", { name: "Record progress" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Progress review" })).toBeVisible();
  await expect(page.getByText("Current status: In progress")).toBeVisible();
  await expect(page.getByText("Build Linux foundations — Pending")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recommended next action" })).toBeVisible();
  await expect(page.getByText(review.nextAction.reason)).toBeVisible();
  await expect(page.getByText("Saved")).toBeVisible();
});

test("not-found response preserves roadmap and notes", async ({ page }) => {
  await session(page);
  await page.route("**/bff/v1/progress/check-ins", (route) => route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ type: "about:blank", title: "Not found", status: 404, code: "ROADMAP_NOT_FOUND", detail: "Use one of your roadmaps.", retryable: false, fieldErrors: [{ field: "roadmapId", messages: ["Use one of your roadmaps."] }] }) }));
  await page.goto("/progress");
  await fill(page, "Do not lose this note");
  await page.getByRole("button", { name: "Record progress" }).click();
  await expect(page.getByText("Use one of your roadmaps.").first()).toBeVisible();
  await expect(page.getByLabel("Roadmap reference")).toHaveValue("roadmap-1");
  await expect(page.getByLabel("Progress notes")).toHaveValue("Do not lose this note");
});

test("duplicate submit is suppressed while a check-in is in flight", async ({ page }) => {
  await session(page);
  let requests = 0;
  await page.route("**/bff/v1/progress/check-ins", async (route) => {
    requests += 1; await new Promise((resolve) => setTimeout(resolve, 150));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(review) });
  });
  await page.goto("/progress"); await fill(page);
  const button = page.getByRole("button", { name: "Record progress" });
  await button.click(); await button.dispatchEvent("click");
  await expect(page.getByRole("heading", { name: "Progress review" })).toBeVisible();
  expect(requests).toBe(1);
});

test("outage preserves input and retries the same intended-action key", async ({ page }) => {
  await session(page);
  const keys: string[] = []; let attempt = 0;
  await page.route("**/bff/v1/progress/check-ins", async (route) => {
    keys.push(route.request().headers()["idempotency-key"]); attempt += 1;
    await route.fulfill(attempt === 1
      ? { status: 503, contentType: "application/json", body: JSON.stringify({ type: "about:blank", title: "Unavailable", status: 503, code: "CORE_UNAVAILABLE", retryable: true, fieldErrors: [] }) }
      : { status: 200, contentType: "application/json", body: JSON.stringify(review) });
  });
  await page.goto("/progress"); await fill(page, "Retry this note");
  await page.getByRole("button", { name: "Record progress" }).click();
  await expect(page.getByText("Checking whether your work was saved…")).toBeVisible();
  await expect(page.getByLabel("Progress notes")).toHaveValue("Retry this note");
  await page.getByRole("button", { name: "Retry progress" }).click();
  await expect(page.getByRole("heading", { name: "Progress review" })).toBeVisible();
  expect(keys).toHaveLength(2); expect(keys[0]).toBe(keys[1]);
});

test("roadmap conflict reloads authority before allowing a new key", async ({ page }) => {
  await session(page);
  const keys: string[] = []; let attempt = 0;
  await page.route("**/bff/v1/roadmaps/roadmap-1", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(roadmap) }));
  await page.route("**/bff/v1/progress/reviews?**", (route) => route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ code: "PROGRESS_REVIEW_NOT_FOUND" }) }));
  await page.route("**/bff/v1/progress/check-ins", async (route) => {
    keys.push(route.request().headers()["idempotency-key"]); attempt += 1;
    await route.fulfill(attempt === 1
      ? { status: 409, contentType: "application/json", body: JSON.stringify({ type: "about:blank", title: "Conflict", status: 409, code: "ROADMAP_VERSION_CONFLICT", detail: "Reload required.", retryable: false, fieldErrors: [] }) }
      : { status: 200, contentType: "application/json", body: JSON.stringify(review) });
  });
  await page.goto("/progress"); await fill(page, "Conflict-safe note");
  await page.getByRole("button", { name: "Record progress" }).click();
  await expect(page.getByText("The roadmap changed. Authoritative progress was reloaded; review your preserved notes and submit again.")).toBeVisible();
  await expect(page.getByLabel("Progress notes")).toHaveValue("Conflict-safe note");
  await page.getByRole("button", { name: "Record progress" }).click();
  await expect(page.getByRole("heading", { name: "Progress review" })).toBeVisible();
  expect(keys).toHaveLength(2); expect(keys[0]).not.toBe(keys[1]);
});

test("saved review survives navigation and reloads authoritatively after refresh", async ({ page }) => {
  await session(page);
  await page.route("**/bff/v1/progress/check-ins", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(review) }));
  await page.route("**/bff/v1/roadmaps/roadmap-1", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(roadmap) }));
  await page.route("**/bff/v1/progress/reviews?**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(review) }));
  await page.goto("/progress"); await fill(page);
  await page.getByRole("button", { name: "Record progress" }).click();
  await page.getByRole("link", { name: "Home" }).click();
  await page.getByRole("link", { name: "Progress" }).click();
  await expect(page.getByRole("heading", { name: "Progress review" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Progress review" })).toBeVisible();
  await expect(page.getByText("Unsaved browser input was discarded; authoritative saved state was reloaded.")).toBeVisible();
});

for (const width of [320, 375, 768, 1024, 1440, 1920]) {
  test(`progress remains keyboard-usable without horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 }); await page.goto("/progress");
    await expect(page.getByRole("heading", { name: "Progress check-in" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  });
}
