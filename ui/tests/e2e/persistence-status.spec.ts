import { expect, test } from "@playwright/test";

test("foundation shell exposes compatibility status without durable browser state", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText("Checking service compatibility");
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
});

for (const journey of ["/roadmaps", "/guidance", "/learning/session-1", "/progress"]) {
  test(`${journey} begins in the explicit not_yet_saved state without durable browser data`, async ({ page }) => {
    await page.goto(journey);
    await expect(page.locator('[role="status"][data-state="not_yet_saved"]')).toHaveText("Not yet saved");
    expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  });
}
