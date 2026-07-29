import { expect, test } from "@playwright/test";
import { signIn, snapshot } from "./helpers";

test("faculty journey covers analytics and assessment review", async ({ browser }, testInfo) => {
  const { page, context } = await signIn(browser, {
    email: "faculty1@spip.com",
    password: "Faculty@123",
  });

  try {
    await page.goto("/dashboard/analytics");
    await expect(page.getByRole("button", { name: /Faculty View/i })).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /Faculty View/i }).click();
    await expect(page.getByText(/Total Students/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("heading", { name: "Class Average" }).first()).toBeVisible();
    await expect(page.getByText(/At-Risk Students/i)).toBeVisible();
    await expect(page.getByText(/Topic Mastery/i)).toBeVisible();
    await snapshot(page, testInfo, "faculty-analytics");

    await page.goto("/dashboard/assessments");
    await expect(page.getByRole("heading", { name: /Assessments/i })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("link", { name: /Start Assessment/i }).first()).toBeVisible();
    await snapshot(page, testInfo, "faculty-assessments");

    await page.goto("/dashboard/interviews");
    await expect(page.getByText(/AI Interview Platform/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/Recent sessions/i)).toBeVisible();
    await snapshot(page, testInfo, "faculty-interviews");

    await page.goto("/dashboard/notifications");
    await expect(page.getByRole("heading", { name: /Your Inbox/i })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("button", { name: /Refresh/i })).toBeVisible();
  } finally {
    await context.close();
  }
});
