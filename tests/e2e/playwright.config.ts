import { defineConfig, devices } from "@playwright/test";

/**
 * E2E tests run against an already-running stack (see docs/runbooks/local-development.md):
 *   WEB_BASE_URL  – Next.js origin (default http://localhost:3000)
 *   API_BASE_URL  – FastAPI origin (default http://localhost:8000)
 * In CI both are started by the workflow before this runs.
 */
const WEB_BASE_URL = process.env.WEB_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./specs",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  ...(process.env.CI ? { workers: 2 } : {}),
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: WEB_BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    locale: "ar-EG",
    timezoneId: "Africa/Cairo",
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
});
