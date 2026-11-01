import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function expectNoSeriousAxeViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  const serious = results.violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  );
  expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
}

test.describe("Phase 2 authentication", () => {
  test.describe.configure({ timeout: 180_000 });

  async function open(page: Page, path: string) {
    await page.goto(path, { waitUntil: "domcontentloaded" });
    // Client session chrome only mounts after hydration; filling before that is wiped.
    await expect(page.getByTestId("sign-in").or(page.getByTestId("sign-out"))).toBeVisible({
      timeout: 30_000,
    });
  }

  for (const { locale, dir } of [
    { locale: "ar", dir: "rtl" },
    { locale: "en", dir: "ltr" },
  ]) {
    test(`register page renders in ${locale}`, async ({ page }) => {
      await open(page, `/${locale}/auth/register`);
      await expect(page.locator("html")).toHaveAttribute("dir", dir);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.locator("#email")).toBeVisible();
      await expect(page.getByTestId("sign-in")).toBeVisible();
    });

    test(`register page has no serious accessibility violations (${locale})`, async ({ page }) => {
      await open(page, `/${locale}/auth/register`);
      await expectNoSeriousAxeViolations(page);
    });

    test(`sign-in page has no serious accessibility violations (${locale})`, async ({ page }) => {
      await open(page, `/${locale}/auth/sign-in`);
      await expect(page.locator("#email")).toBeVisible();
      await expectNoSeriousAxeViolations(page);
    });
  }

  test("register, sign in, open account, sign out", async ({ page }) => {
    const email = `e2e-${crypto.randomUUID()}@example.com`;
    const password = "correct-horse-battery-staple";

    await open(page, "/en/auth/register");
    await page.locator("#email").fill(email);
    await page.locator("#password").fill(password);
    await page.locator("#displayName").fill("E2E Rider");
    await page.locator("#fullName").fill("E2E Test Passenger");
    await page.locator("#dateOfBirth").fill("1990-01-15");
    await page.locator("#accepted").check();
    await page.locator("form").getByRole("button").click();

    await expect(page).toHaveURL(/\/en\/auth\/check-email/, { timeout: 30_000 });
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await open(page, "/en/auth/sign-in");
    await page.locator("#email").fill(email);
    await page.locator("#password").fill(password);
    await page.locator("form").getByRole("button").click();

    await expect(page.getByTestId("sign-out")).toBeVisible({ timeout: 30_000 });
    await expect(page).toHaveURL(/\/en\/me/, { timeout: 60_000 });
    await expect(page.getByText(email)).toBeVisible();

    await page.getByTestId("sign-out").click();
    await expect(page.getByTestId("sign-in")).toBeVisible();
  });
});
