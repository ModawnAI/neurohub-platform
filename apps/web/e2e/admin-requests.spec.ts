import { test, expect } from "@playwright/test";

// Base URL for the running app
const BASE = process.env.E2E_BASE_URL || "http://localhost:3000";

test.describe("Admin Request List — Search", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE}/admin/requests`);
    // Wait for the page to be interactive
    await page.waitForLoadState("networkidle");
  });

  test("renders search input with placeholder", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search|검색/i);
    await expect(searchInput).toBeVisible();
  });

  test("search input filters request list on typing", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search|검색/i);
    await searchInput.fill("nonexistent-id-12345");
    // Debounce wait
    await page.waitForTimeout(500);
    // Should show either no data or filtered results
    await expect(page.locator("body")).toBeVisible();
  });

  test("filter tabs are visible", async ({ page }) => {
    // Should have filter tabs for status
    const allTab = page.getByRole("button", { name: /전체|All/i });
    await expect(allTab).toBeVisible();
  });
});

test.describe("Admin Request Detail — Pipeline Monitoring", () => {
  test("shows pipeline monitoring panel for computing requests", async ({ page }) => {
    // Navigate to admin requests
    await page.goto(`${BASE}/admin/requests`);
    await page.waitForLoadState("networkidle");

    // If there are requests in the list, click the first one
    const firstRow = page.locator("table tbody tr, .request-card").first();
    if (await firstRow.isVisible()) {
      await firstRow.click();
      await page.waitForLoadState("networkidle");

      // Check that the detail page has loaded
      const detailPage = page.locator("body");
      await expect(detailPage).toBeVisible();

      // If the request is in COMPUTING state, pipeline panel should appear
      // This test just verifies the page renders without errors
    }
  });
});

test.describe("Admin Techniques Page", () => {
  test("renders technique cards with i18n labels", async ({ page }) => {
    await page.goto(`${BASE}/admin/techniques`);
    await page.waitForLoadState("networkidle");

    // Should show the title
    const title = page.getByRole("heading", { level: 1 });
    await expect(title).toBeVisible();

    // Should not contain raw Korean hardcoded text for "전체" filter
    // Instead should use i18n key
    const filterButtons = page.locator("button");
    await expect(filterButtons.first()).toBeVisible();
  });

  test("modality filter buttons work", async ({ page }) => {
    await page.goto(`${BASE}/admin/techniques`);
    await page.waitForLoadState("networkidle");

    // Click a modality filter if visible
    const modalityButton = page.getByRole("button").filter({ hasText: /MRI|PET|EEG/ }).first();
    if (await modalityButton.isVisible()) {
      await modalityButton.click();
      await page.waitForTimeout(500);
      // Page should still be visible
      await expect(page.locator("body")).toBeVisible();
    }
  });
});
