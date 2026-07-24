import { expect, test } from "@playwright/test";

test("unknown routes reject direct entry and focus the outcome", async ({ page }) => {
  await page.goto("/not-a-route");
  await expect(page.getByRole("heading", { level: 1, name: "Page not found" })).toBeVisible();
  await expect(page.locator("main")).toBeFocused();
});

for (const route of ["/roadmaps", "/guidance", "/learning/session-1", "/progress"]) {
  test(`${route} restores route focus without durable browser state`, async ({ page }) => {
    await page.goto(route);
    await expect(page.locator("main")).toBeFocused();
    await page.getByRole("link", { name: "Home" }).click();
    await expect(page.locator("main")).toBeFocused();
    await page.goBack();
    await expect(page.locator("main")).toBeFocused();
    expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  });
}
