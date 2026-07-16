import { expect, test } from "@playwright/test";

async function completeForm(page: import("@playwright/test").Page, topic = "K8S") {
  await page.getByLabel("Guidance topic").fill(topic);
  await page.getByLabel("Current role").fill("Administrator");
  await page.getByLabel("Experience level").selectOption("beginner");
  await page.getByLabel("Target role").fill("Platform engineer");
}

const success = {
  requestedTopic: "K8S", resolvedTopic: "Kubernetes", supported: true,
  topicSummary: "Run containerized workloads safely.", currentLevelFit: "A useful next step.",
  practicalNextAction: "Deploy a small workload.", commonPitfalls: ["Skipping resource limits"],
  relatedTopics: ["Helm"], suggestions: [], notes: [],
  labReferences: [{ id: "lab-1", provider: "Approved provider", objective: "Deploy", prerequisites: [], estimatedMinutes: 20, costStatus: "free", availabilityStatus: "active", destinationUrl: "https://example.test/lab" }],
};

test("renders canonical guidance, safe lab metadata, and exact timing marks", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 760 });
  await page.route("**/bff/v1/guidance", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(success) }));
  await page.goto("/guidance");
  await completeForm(page);
  await page.getByRole("button", { name: "Get guidance" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Guidance for Kubernetes" })).toBeVisible();
  await expect(page.getByText("Requested topic: K8S")).toBeVisible();
  await expect(page.getByText("Cost: free")).toBeVisible();
  const lab = page.getByRole("link", { name: "Open lab in a new tab" });
  await expect(lab).toHaveAttribute("target", "_blank");
  await expect(lab).toHaveAttribute("rel", "noopener noreferrer");
  expect(await page.evaluate(() => performance.getEntriesByName("guidance.result.fetch-resolved").length)).toBe(1);
  expect(await page.evaluate(() => performance.getEntriesByName("guidance.result.accessible-render-committed").length)).toBe(1);
});

for (const outcome of [
  { name: "unavailable", code: "GUIDANCE_TOPIC_UNAVAILABLE", retryable: true, detail: "This topic is temporarily unavailable." },
  { name: "retired", code: "GUIDANCE_TOPIC_UNAVAILABLE", retryable: false, detail: "This topic has been retired." },
  { name: "uninterpretable", code: "GUIDANCE_TOPIC_UNINTERPRETABLE", retryable: false, detail: "Choose a catalog topic." },
]) {
test(`preserves topic and profile for ${outcome.name} outcomes`, async ({ page }) => {
  await page.route("**/bff/v1/guidance", (route) => route.fulfill({ status: 422, contentType: "application/json", body: JSON.stringify({ type: "about:blank", title: "Rejected", status: 422, traceId: "trace", fieldErrors: [{ field: "topic", messages: [outcome.detail] }], ...outcome }) }));
  await page.goto("/guidance");
  await completeForm(page, "Legacy topic");
  await page.getByRole("button", { name: "Get guidance" }).click();
  await expect(page.getByText(outcome.detail, { exact: true }).first()).toBeVisible();
  await expect(page.getByLabel("Guidance topic")).toHaveValue("Legacy topic");
  await expect(page.getByLabel("Current role")).toHaveValue("Administrator");
  await expect(page.getByRole("button", { name: outcome.retryable ? "Retry guidance" : "Get guidance" })).toBeVisible();
});
}

test("outage retains values and retries with the same operation key", async ({ page }) => {
  const keys: string[] = [];
  let attempt = 0;
  await page.route("**/bff/v1/guidance", async (route) => {
    keys.push(route.request().headers()["idempotency-key"]);
    attempt += 1;
    await route.fulfill(attempt === 1
      ? { status: 503, contentType: "application/json", body: JSON.stringify({ type: "about:blank", title: "Unavailable", status: 503, code: "CORE_UNAVAILABLE", retryable: true, fieldErrors: [], traceId: "trace" }) }
      : { status: 200, contentType: "application/json", body: JSON.stringify(success) });
  });
  await page.goto("/guidance");
  await completeForm(page);
  await page.getByRole("button", { name: "Get guidance" }).click();
  await expect(page.getByText("Checking whether your work was saved…")).toBeVisible();
  await page.getByRole("button", { name: "Retry guidance" }).click();
  await expect(page.getByRole("heading", { name: "Guidance for Kubernetes" })).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
});

test("suppresses a duplicate submit while guidance is in flight", async ({ page }) => {
  let requests = 0;
  await page.route("**/bff/v1/guidance", async (route) => {
    requests += 1;
    await new Promise((resolve) => setTimeout(resolve, 150));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(success) });
  });
  await page.goto("/guidance");
  await completeForm(page);
  const button = page.getByRole("button", { name: "Get guidance" });
  await button.click();
  await button.dispatchEvent("click");
  await expect(page.getByRole("heading", { name: "Guidance for Kubernetes" })).toBeVisible();
  expect(requests).toBe(1);
});

test("local validation is field-associated and sends no request", async ({ page }) => {
  let requests = 0;
  page.on("request", (request) => { if (request.url().includes("/bff/v1/guidance")) requests += 1; });
  await page.goto("/guidance");
  await page.getByRole("button", { name: "Get guidance" }).click();
  await expect(page.getByLabel("Guidance topic")).toBeFocused();
  await expect(page.getByLabel("Guidance topic")).toHaveAttribute("aria-invalid", "true");
  expect(requests).toBe(0);
});

for (const width of [320, 375, 768, 1024, 1440, 1920]) {
  test(`guidance remains keyboard-usable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/guidance");
    await page.keyboard.press("Tab");
    await expect(page.getByRole("heading", { name: "Skill guidance" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  });
}
