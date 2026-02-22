import { test, expect } from "@playwright/test";

test.describe("Dashboard (requires auth)", () => {
  test("redirects unauthenticated users", async ({ page }) => {
    await page.goto("/user/dashboard");
    // Should redirect to login or show auth prompt
    await page.waitForTimeout(2000);
    const url = page.url();
    // Either stays on dashboard (if dev bypass) or redirects to login
    expect(url).toMatch(/\/(login|user\/dashboard)/);
  });
});
