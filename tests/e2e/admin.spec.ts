import { expect, test } from "@playwright/test";
import { fixtures, signIn, snapshot } from "./helpers";

test("admin journey covers analytics, providers, knowledge, and notifications", async ({ browser }, testInfo) => {
  const { page, context } = await signIn(browser, {
    email: "admin@spip.com",
    password: "Admin@123",
  });

  try {
    await page.goto("/dashboard/analytics");
    await expect(page.getByRole("button", { name: /System Admin/i })).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /System Admin/i }).click();
    await expect(page.getByText(/System Status/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("heading", { name: "AI Requests" }).first()).toBeVisible();
    await expect(page.getByText(/AI Provider Monitor/i)).toBeVisible();
    await snapshot(page, testInfo, "admin-analytics");

    await page.goto("/dashboard/admin/ai-providers");
    await expect(page.getByText(/Multi-Provider Orchestration/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("button", { name: /Refresh/i })).toBeVisible();
    await snapshot(page, testInfo, "admin-ai-providers");

    await page.goto("/dashboard/admin/knowledge");
    await expect(page.getByText(/Enterprise Knowledge Engine/i)).toBeVisible({ timeout: 30000 });
    await page.locator("#file-upload").setInputFiles(fixtures().knowledgeTxt);
    await page.getByRole("button", { name: /Process Document/i }).click();
    await expect(page.getByText(/queued for processing|Upload successful/i)).toBeVisible({ timeout: 30000 });
    await page.locator('input[placeholder="Search term, topic, or module name"]').fill("roadmap");
    await page.getByRole("button", { name: /Inspect retrieval/i }).click();
    await expect(page.getByText(/No retrieval results yet|Document \/ Chunk/i)).toBeVisible({ timeout: 30000 });
    await snapshot(page, testInfo, "admin-knowledge");

    await page.goto("/dashboard/admin/notifications");
    await expect(page.getByText(/Notification Engine/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("button", { name: /Send Broadcast/i }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: /Queue & Logs/i }).first()).toBeVisible();
    await page.getByRole("button", { name: /Queue & Logs/i }).first().click();
    await expect(page.getByRole("button", { name: /Send Broadcast/i }).first()).toBeVisible({ timeout: 30000 });
    await snapshot(page, testInfo, "admin-notifications");
  } finally {
    await context.close();
  }
});
