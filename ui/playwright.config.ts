import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: "http://127.0.0.1:4173", trace: "on-first-retry" },
  webServer: {
    command: "npm run build && npm run preview",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: "chrome-stable", use: { ...devices["Desktop Chrome"], channel: "chrome" } },
    { name: "chromium-current", use: { ...devices["Desktop Chrome"] } },
    { name: "edge-stable", use: { ...devices["Desktop Edge"], channel: "msedge" } },
    { name: "firefox-current", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit-current", use: { ...devices["Desktop Safari"] } },
    { name: "mobile-chrome-portrait", use: { ...devices["Pixel 7"] } },
    { name: "mobile-chrome-landscape", use: { ...devices["Pixel 7 landscape"] } },
    { name: "mobile-webkit-portrait", use: { ...devices["iPhone 15"] } },
    { name: "mobile-webkit-landscape", use: { ...devices["iPhone 15 landscape"] } }
  ]
});
