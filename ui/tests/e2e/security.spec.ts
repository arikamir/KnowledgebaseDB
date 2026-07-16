import { expect, test } from "@playwright/test";

test("keeps browser authentication and personalized inputs out of durable storage", async ({ page }) => {
  await page.goto("/roadmaps");
  await page.getByLabel("Current role").fill("Sensitive role value");
  await page.getByLabel("Target role").fill("Sensitive target value");

  const durableState = await page.evaluate(async () => ({
    local: { ...localStorage },
    session: { ...sessionStorage },
    databases: indexedDB.databases ? await indexedDB.databases() : [],
    serviceWorkers: "serviceWorker" in navigator ? (await navigator.serviceWorker.getRegistrations()).length : 0,
    caches: "caches" in window ? await caches.keys() : [],
  }));

  expect(durableState.local).toEqual({});
  expect(durableState.session).toEqual({});
  expect(durableState.databases).toEqual([]);
  expect(durableState.serviceWorkers).toBe(0);
  expect(durableState.caches).toEqual([]);
});

test("does not send browser credentials or persist submitted profile data", async ({ page }) => {
  let headers: Record<string, string> = {};
  await page.route("**/bff/v1/roadmaps", async (route) => {
    headers = route.request().headers();
    await route.fulfill({
      status: 503,
      contentType: "application/problem+json",
      body: JSON.stringify({
        type: "about:blank", title: "Unavailable", status: 503,
        code: "CORE_UNAVAILABLE", retryable: true, traceId: "safe-trace",
        debug: "Bearer must-not-render", fieldErrors: [],
      }),
    });
  });
  await page.goto("/roadmaps");
  await page.getByLabel("Current role").fill("Administrator");
  await page.getByLabel("Experience level").selectOption("beginner");
  await page.getByLabel("Target role").fill("Platform engineer");
  await page.getByLabel("Hours available per week").fill("5");
  await page.getByRole("button", { name: "Create roadmap" }).click();

  await expect(page.getByText("Checking whether your work was saved…")).toBeVisible();
  await expect(page.getByText("Bearer must-not-render")).toHaveCount(0);
  expect(headers.authorization).toBeUndefined();
  expect(headers.cookie).toBeUndefined();
  expect(headers["x-csrf-token"]).toBeUndefined();
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).not.toContain("Administrator");
});
