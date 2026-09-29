import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

test.describe("Phase 1 smoke", () => {
  test("API liveness and readiness respond", async ({ request }) => {
    const live = await request.get(`${API_BASE_URL}/health/live`);
    expect(live.ok()).toBe(true);
    expect(live.headers()["x-request-id"]).toBeTruthy();

    const ready = await request.get(`${API_BASE_URL}/health/ready`);
    expect(ready.ok()).toBe(true);
    const body = (await ready.json()) as { status: string };
    expect(body.status).toBe("ok");
  });

  test("API returns RFC 9457 problem details for unknown routes", async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/api/v1/does-not-exist`);
    expect(response.status()).toBe(404);
    expect(response.headers()["content-type"]).toContain("application/problem+json");
    const problem = (await response.json()) as { code: string; requestId: string };
    expect(problem.code).toBe("NOT_FOUND");
    expect(problem.requestId).toBeTruthy();
  });

  test("root redirects to the default (Arabic) locale", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/ar$/);
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  });

  for (const { locale, dir } of [
    { locale: "ar", dir: "rtl" },
    { locale: "en", dir: "ltr" },
  ]) {
    test(`landing page renders in ${locale} and reaches the API`, async ({ page }) => {
      await page.goto(`/${locale}`);
      await expect(page.locator("html")).toHaveAttribute("dir", dir);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.getByTestId("system-status")).toBeVisible();
      // The API is reachable from the web server: status shows the environment name.
      await expect(page.getByTestId("system-status-value")).toContainText(
        /development|test|staging/,
      );
    });

    test(`landing page has no serious accessibility violations (${locale})`, async ({ page }) => {
      await page.goto(`/${locale}`);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
        .analyze();
      const serious = results.violations.filter(
        (v) => v.impact === "serious" || v.impact === "critical",
      );
      expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
    });
  }

  test("language switcher changes locale and direction", async ({ page }) => {
    await page.goto("/ar");
    await page.getByTestId("language-switcher").selectOption("en");
    await expect(page).toHaveURL(/\/en$/);
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  });

  test("unknown path under a locale renders the localised 404", async ({ page }) => {
    const response = await page.goto("/en/this-route-does-not-exist");
    expect(response?.status()).toBe(404);
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });
});
