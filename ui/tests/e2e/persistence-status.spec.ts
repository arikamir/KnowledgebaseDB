import { expect, test } from "@playwright/test";

test("foundation shell exposes compatibility status without durable browser state", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText("Checking service compatibility");
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
});
