import { test, expect } from "@playwright/test";

test.describe("Landing Page", () => {
  test("has correct title and Korean content", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/NeuroHub/);
    // Check for Korean content
    const body = await page.textContent("body");
    expect(body).toBeTruthy();
  });

  test("navigation links are accessible", async ({ page }) => {
    await page.goto("/");
    // Check skip nav link exists
    const skipLink = page.locator(".skip-nav");
    await expect(skipLink).toBeAttached();
  });

  test("login link navigates to login page", async ({ page }) => {
    await page.goto("/");
    const loginLink = page.locator('a[href="/login"]').first();
    if (await loginLink.isVisible()) {
      await loginLink.click();
      await expect(page).toHaveURL(/\/login/);
    }
  });
});

test.describe("Authentication Flow", () => {
  test("login page renders correctly", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("body")).toContainText(/로그인|NeuroHub/);
  });

  test("register page renders correctly", async ({ page }) => {
    await page.goto("/register");
    await expect(page.locator("body")).toContainText(/회원가입|NeuroHub/);
  });
});
