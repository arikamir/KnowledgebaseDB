import { expect, test } from "@playwright/test";

test("creates and accessibly renders a roadmap at mobile width", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.route("**/bff/v1/roadmaps", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ready", roadmap: { id: "one", milestones: [{ id: "m1", title: "Container fundamentals", concreteNextAction: "Build an image" }] } }) }));
  await page.goto("/roadmaps");
  await page.getByLabel("Current role").fill("Administrator");
  await page.getByLabel("Experience level").selectOption("beginner");
  await page.getByLabel("Target role").fill("DevOps Engineer");
  await page.getByLabel("Hours available per week").fill("5");
  await page.getByRole("button", { name: "Create roadmap" }).click();
  await expect(page.getByRole("heading", { name: "Your career roadmap" })).toBeVisible();
  await expect(page.getByText("Container fundamentals")).toBeVisible();
  expect(await page.evaluate(() => performance.getEntriesByName("career.result.accessible-render-committed").length)).toBe(1);
  expect(await page.evaluate(() => performance.getEntriesByName("career.result.fetch-resolved").length)).toBe(1);
});

for (const width of [320, 375, 768, 1024, 1440, 1920]) {
  test(`roadmap form remains usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/roadmaps");
    await expect(page.getByRole("heading", { name: "Build your roadmap" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  });
}

test("local errors are associated without a network request", async ({ page }) => {
  let requests = 0;
  page.on("request", (request) => { if (request.url().includes("/bff/v1/roadmaps")) requests += 1; });
  await page.goto("/roadmaps");
  await page.getByRole("button", { name: "Create roadmap" }).click();
  await expect(page.getByText("Enter your current role.")).toBeVisible();
  await expect(page.getByLabel("Current role")).toHaveAttribute("aria-invalid", "true");
  expect(requests).toBe(0);
});

test("outage preserves entered profile values", async ({ page }) => {
  await page.route("**/bff/v1/roadmaps", async (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "CORE_UNAVAILABLE" }) }));
  await page.goto("/roadmaps");
  await page.getByLabel("Current role").fill("Administrator");
  await page.getByLabel("Experience level").selectOption("beginner");
  await page.getByLabel("Target role").fill("DevOps Engineer");
  await page.getByLabel("Hours available per week").fill("5");
  await page.getByRole("button", { name: "Create roadmap" }).press("Enter");
  await expect(page.getByText(/Checking whether your work was saved/)).toBeVisible();
  await expect(page.getByLabel("Current role")).toHaveValue("Administrator");
});
