import { expect, test } from "@playwright/test";
import { signIn, snapshot } from "./helpers";

test("learning hub is roadmap-first and lesson sources are visible", async ({ browser }, testInfo) => {
  const { page, context } = await signIn(browser, {
    email: "student1@spip.com",
    password: "Student@123",
  });

  try {
    await page.goto("/dashboard/learning");
    await expect(page.getByText(/Enterprise Learning Hub/i)).toBeVisible({ timeout: 30000 });
    await page.getByPlaceholder("Data Structures").fill("Learning Hub QA Roadmap");
    await page.getByPlaceholder("Computer Science").fill("Computer Science");
    await page.getByPlaceholder("Intermediate").fill("Intermediate");
    await page.getByPlaceholder("8").fill("6");
    await page.getByRole("button", { name: /Generate roadmap/i }).click();
    await page.waitForURL(/\/dashboard\/learning\/module\/\d+/, { timeout: 30000 });
    await expect(page.getByRole("tab", { name: "Sources", exact: true })).toBeVisible({ timeout: 30000 });
    await page.getByRole("tab", { name: "Sources", exact: true }).click();
    await expect(page.getByText(/Retrieved sources will appear here|Retrieved chunks/i).first()).toBeVisible({ timeout: 30000 });
    await snapshot(page, testInfo, "learning-module-sources");

    await page.goto("/dashboard/learning");
    await page.getByPlaceholder("Trees and Graphs").fill("Learning Hub QA Session");
    await page.getByPlaceholder("Algorithms").fill("Algorithms");
    await page.getByRole("button", { name: /Start study session/i }).click();
    await expect(page).toHaveURL(/\/dashboard\/learning\/chat\/\d+/);
    await expect(page.getByText(/Study Assistant/i)).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /Summary/i }).click();
    await expect(page.getByRole("heading", { name: /Summary/i })).toBeVisible({ timeout: 30000 });
    await snapshot(page, testInfo, "learning-study-session");
  } finally {
    await context.close();
  }
});
