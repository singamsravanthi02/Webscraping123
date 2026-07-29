import { expect, test } from "@playwright/test";
import { signUpPlacementOfficer, snapshot } from "./helpers";

test("placement journey covers analytics and jobs", async ({ browser }, testInfo) => {
  const email = `placement.qa.${Date.now()}@spip.com`;
  const password = "Placement@123!";
  const { page, context } = await signUpPlacementOfficer(browser, { email, password });

  try {
    await page.goto("/dashboard/analytics");
    await expect(page.getByRole("button", { name: /Placement Officer/i })).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /Placement Officer/i }).click();
    await expect(page.getByText(/Active Drives/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("heading", { name: "Recommendations" }).first()).toBeVisible();
    await expect(page.getByText(/Avg Match Score/i)).toBeVisible();
    await expect(page.getByText(/Job Source Mix/i)).toBeVisible();
    await snapshot(page, testInfo, "placement-analytics");

    await page.goto("/dashboard/jobs");
    await expect(page.getByRole("heading", { name: /Job Discovery/i })).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/AI Job Assistant/i)).toBeVisible();
    await page.getByLabel(/Remote only/i).check();
    await expect(page.getByText(/(Posted (today|yesterday|\d+ days ago)|Freshness unknown)/i).first()).toBeVisible({ timeout: 30000 });
    await snapshot(page, testInfo, "placement-jobs");

    await page.goto("/dashboard/notifications");
    await expect(page.getByRole("heading", { name: /Your Inbox/i })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("button", { name: /Refresh/i })).toBeVisible();
  } finally {
    await context.close();
  }
});
