import { expect, test, type Page } from "@playwright/test";

const journeys = [
  { path: "/roadmaps", heading: "Career roadmap" },
  { path: "/guidance", heading: "Skill guidance" },
  { path: "/learning/session-1", heading: "Focused learning" },
  { path: "/progress", heading: "Progress check-in" },
];
const widths = [320, 375, 768, 1024, 1440, 1920];

async function assertAccessibleStructure(page: Page, heading: string) {
  await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
  await expect(page.locator("main")).toBeFocused();
  expect(await page.locator("h1").count()).toBe(1);
  expect(await page.evaluate(() => {
    const levels = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].map((node) => Number(node.tagName.slice(1)));
    return levels.every((level, index) => index === 0 || level <= levels[index - 1] + 1);
  })).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const interactive = page.locator("a,button,input,select,textarea,[tabindex]:not([tabindex='-1'])");
  for (let index = 0; index < await interactive.count(); index += 1) {
    const item = interactive.nth(index);
    if (await item.isVisible()) await expect(item).toHaveAccessibleName(/\S/);
  }
  await page.keyboard.press("Tab");
  const focus = page.locator(":focus");
  await expect(focus).toBeVisible();
  expect(await focus.evaluate((node) => Number.parseFloat(getComputedStyle(node).outlineWidth))).toBeGreaterThanOrEqual(2);
}

for (const journey of journeys) {
  for (const width of widths) {
    test(`${journey.path} has one ordered heading, named controls, focus, and no loss at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      await page.goto(journey.path);
      await assertAccessibleStructure(page, journey.heading);
    });
  }

  test(`${journey.path} survives 200% text scaling`, async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto(journey.path);
    await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
    await expect(page.getByRole("heading", { level: 1, name: journey.heading })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  });
}

test("blocking validation is assertive, field-associated, focused, and not repeated", async ({ page }) => {
  await page.goto("/roadmaps");
  await page.getByRole("button", { name: "Create roadmap" }).click();
  const field = page.getByLabel("Current role");
  await expect(field).toBeFocused();
  await expect(field).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByRole("alert")).toHaveCount(4);
  await expect(page.getByText("Enter your current role.")).toHaveCount(1);
});

test("status regions are polite and external lab actions expose provider, cost, duration, and new-tab behavior", async ({ page }) => {
  await page.goto("/guidance");
  for (const status of await page.getByRole("status").all()) await expect(status).toHaveAttribute("aria-live", "polite");
  await page.goto("/learning/session-1");
  const external = page.getByRole("link", { name: /Open lab in a new tab/ });
  if (await external.count()) {
    await expect(external).toHaveAttribute("target", "_blank");
    await expect(page.getByText(/Cost:/)).toBeVisible();
    await expect(page.getByText(/Estimated time:/)).toBeVisible();
    await expect(page.getByRole("heading", { name: /lab$/i })).toBeVisible();
  }
});
