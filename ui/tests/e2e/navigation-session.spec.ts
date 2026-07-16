import { expect, test } from "@playwright/test";

test("inactive story routes reject direct entry and focus the outcome", async ({ page }) => {
  await page.goto("/guidance");
  await expect(page.getByRole("heading", { level: 1, name: "Page not found" })).toBeVisible();
  await expect(page.locator("main")).toBeFocused();
});
