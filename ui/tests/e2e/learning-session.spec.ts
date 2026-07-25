import { expect, test } from "@playwright/test";

const session = { id: "session-1", roadmapId: "roadmap", contentVersion: "v1", questionVersion: "q1", labReferenceVersions: ["lab-1"], title: "Kubernetes practice", objective: "Deploy safely", estimatedMinutes: 25, status: "in_progress", currentStepOrdinal: 0, retirement: { status: "published", securityCritical: false }, steps: [{ id: "read", ordinal: 0, stepType: "reading", title: "Read the deployment guide", status: "pending" }, { id: "lab", ordinal: 1, stepType: "lab", title: "Practice deployment", status: "pending", labReference: { id: "lab-1", provider: "Approved provider", objective: "Deploy", prerequisites: [], estimatedMinutes: 20, costStatus: "free", availabilityStatus: "active", destinationUrl: "https://example.test/lab" } }, { id: "review", ordinal: 2, stepType: "review", title: "Review", status: "pending" }] };
const attempt = { id: "attempt-1", attemptNumber: 1, questionSnapshotVersion: "q1", status: "in_progress", questions: [1, 2, 3].map((value) => ({ id: `q${value}`, ordinal: value - 1, prompt: `Question ${value}?`, choices: { a: "Answer A", b: "Answer B" } })), answers: [], startedAt: "2026-01-01T00:00:00Z", scorePercent: null, passed: null, submittedAt: null };

async function mockLearning(page: import("@playwright/test").Page) {
  await page.route("**/bff/v1/learning-sessions/content-1", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(session) }));
  await page.route("**/bff/v1/learning-sessions/session-1/steps/read/completion", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...session, currentStepOrdinal: 1, steps: session.steps.map((step) => step.id === "read" ? { ...step, status: "completed" } : step) }) }));
  await page.route("**/bff/v1/learning-sessions/session-1/review-attempts", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(route.request().method() === "GET" ? [] : attempt) }));
  await page.route("**/bff/v1/review-attempts/attempt-1/answers/*", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ questionId: "q1", submittedAnswerKey: "a", correct: true, explanation: "That is why.", answeredAt: "2026-01-01T00:01:00Z" }) }));
  await page.route("**/bff/v1/review-attempts/attempt-1/submit", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ attemptId: "attempt-1", scorePercent: 100, passed: true, sessionStatus: "completed", missedQuestionIds: [], nextAction: { kind: "continue_milestone", title: "Continue", reason: "Passed", target: "next" } }) }));
  await page.route("**/bff/v1/lab-references/lab-1/reports", (route) => route.fulfill({ status: 202, contentType: "application/json", body: "{}" }));
}

test("resumes, persists a step, reviews, and completes accessibly", async ({ page }) => {
  await mockLearning(page); await page.setViewportSize({ width: 320, height: 800 }); await page.goto("/learning/content-1");
  await expect(page.getByRole("heading", { name: "Kubernetes practice" })).toBeVisible();
  await page.getByRole("button", { name: "Mark step complete" }).click();
  await expect(page.getByText("Step 2 of 3")).toBeVisible();
  await page.getByRole("button", { name: "Begin review" }).click();
  for (let index = 0; index < 3; index += 1) { await page.getByLabel("Answer A").nth(index).check(); await page.getByRole("button", { name: "Check answer" }).nth(index).click(); }
  await expect(page.getByRole("status").filter({ hasText: "Correct. That is why." })).toBeVisible();
  expect(await page.evaluate(() => performance.getEntriesByName("learning.review.feedback-committed").length)).toBeGreaterThanOrEqual(1);
  await page.getByRole("button", { name: "Submit full review" }).click();
  await expect(page.getByRole("heading", { name: "Learning session complete" })).toBeVisible();
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();
});

test("lab return reloads state without marking the lab complete", async ({ page }) => {
  await mockLearning(page); await page.goto("/learning/content-1");
  const link = page.getByRole("link", { name: "Open lab in a new tab" });
  await expect(link).toHaveAttribute("rel", "noopener noreferrer");
  await page.getByRole("button", { name: "I returned from the lab" }).click();
  await expect(page.getByText("Not completed").nth(1)).toBeVisible();
  await expect(page.getByText("Opening or returning from a lab does not mark it complete.")).toBeVisible();
});

test("outage preserves the route and exposes retry-safe persistence status", async ({ page }) => {
  await page.route("**/bff/v1/learning-sessions/content-1", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "CORE_UNAVAILABLE" }) }));
  await page.route("**/bff/v1/learning-sessions/content-1/start", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "CORE_UNAVAILABLE" }) }));
  await page.goto("/learning/content-1");
  await expect(page.getByText("Checking whether your work was saved…")).toBeVisible();
  await expect(page).toHaveURL(/\/learning\/content-1/);
});

test("restores the lowest incomplete cursor and an in-progress answered attempt", async ({ page }) => {
  const restored = { ...session, currentStepOrdinal: 2, steps: session.steps.map((step) => step.ordinal < 2 ? { ...step, status: "completed" } : step) };
  await page.route("**/bff/v1/learning-sessions/content-1", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(restored) }));
  await page.route("**/bff/v1/learning-sessions/session-1/review-attempts", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ ...attempt, latest: true, answers: [{ questionId: "q1", submittedAnswerKey: "a", correct: true, explanation: "Saved" }] }]) }));
  await page.goto("/learning/content-1");
  await expect(page.getByText("Step 3 of 3")).toBeVisible();
  await expect(page.getByText("Attempt 1 — latest")).toBeVisible();
});

for (const retirement of [
  { name: "normal", value: { status: "retired", securityCritical: false, replacementContentId: "content-2" }, message: /grace period.*Replacement available: content-2/ },
  { name: "security", value: { status: "retired", securityCritical: true }, message: /security reasons and cannot continue/ },
]) test(`shows exact ${retirement.name} retirement guidance`, async ({ page }) => { await mockLearning(page); await page.route("**/bff/v1/learning-sessions/content-1", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...session, retirement: retirement.value }) })); await page.goto("/learning/content-1"); await expect(page.getByRole("alert").filter({ hasText: retirement.message })).toBeVisible(); });

test("suppresses duplicate review starts while the first mutation is pending", async ({ page }) => {
  let starts = 0; await mockLearning(page);
  await page.route("**/bff/v1/learning-sessions/session-1/review-attempts", async (route) => { if (route.request().method() === "GET") return route.fulfill({ status: 200, contentType: "application/json", body: "[]" }); starts += 1; await new Promise((resolve) => setTimeout(resolve, 150)); return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(attempt) }); });
  await page.goto("/learning/content-1"); const button = page.getByRole("button", { name: "Begin review" }); await button.click(); await button.dispatchEvent("click"); await expect(page.getByRole("heading", { name: "Knowledge review" })).toBeVisible(); expect(starts).toBe(1);
});

test("announces rolling retry rate limits while preserving the session", async ({ page }) => {
  await mockLearning(page); await page.route("**/bff/v1/learning-sessions/session-1/review-attempts", (route) => route.request().method() === "GET" ? route.fulfill({ status: 200, contentType: "application/json", body: "[]" }) : route.fulfill({ status: 429, contentType: "application/json", body: JSON.stringify({ code: "REVIEW_RETRY_RATE_LIMITED", retryable: true }) }));
  await page.goto("/learning/content-1"); await page.getByRole("button", { name: "Begin review" }).click(); await expect(page.getByRole("alert", { name: "" }).filter({ hasText: "15 minutes" })).toBeVisible(); await expect(page.getByRole("heading", { name: "Kubernetes practice" })).toBeVisible();
});

test("a delayed response cannot update a route after interruption", async ({ page }) => {
  await page.route("**/bff/v1/learning-sessions/content-1", async (route) => { await new Promise((resolve) => setTimeout(resolve, 200)); await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(session) }); });
  await page.goto("/learning/content-1"); await page.goto("/"); await page.waitForTimeout(250); await expect(page.getByRole("link", { name: "DevOps Career Agent" }).first()).toBeVisible(); await expect(page.getByText("Kubernetes practice")).toHaveCount(0);
});

test("failed review leads to missed-concept study and a fresh no-copy attempt", async ({ page }) => {
  await mockLearning(page); let starts = 0;
  await page.route("**/bff/v1/learning-sessions/session-1/review-attempts", (route) => { if (route.request().method() === "GET") return route.fulfill({ status: 200, contentType: "application/json", body: "[]" }); starts += 1; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ...attempt, id: `attempt-${starts}`, attemptNumber: starts, answers: [] }) }); });
  await page.route("**/bff/v1/review-attempts/attempt-1/submit", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ attemptId: "attempt-1", scorePercent: 60, passed: false, sessionStatus: "retry_required", missedQuestionIds: ["q2"], nextAction: { kind: "retry_material" } }) }));
  await page.goto("/learning/content-1"); await page.getByRole("button", { name: "Begin review" }).click();
  for (let index = 0; index < 3; index += 1) await page.getByLabel("Answer B").nth(index).check();
  await page.getByRole("button", { name: "Submit full review" }).click(); await expect(page.getByRole("heading", { name: "Review missed concepts" })).toBeVisible();
  await page.getByRole("button", { name: "Begin fresh full attempt" }).click(); await expect(page.getByText("Attempt 2")).toBeVisible();
  await expect(page.getByRole("radio").first()).not.toBeChecked();
});

for (const width of [320, 375, 768, 1024, 1440, 1920]) test(`learning layout remains usable at ${width}px`, async ({ page }) => { await mockLearning(page); await page.setViewportSize({ width, height: 800 }); await page.goto("/learning/content-1"); await expect(page.getByRole("heading", { name: "Focused learning" })).toBeVisible(); expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true); });
