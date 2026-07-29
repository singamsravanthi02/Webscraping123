import { expect, test } from "@playwright/test";
import { fixtures, signIn, snapshot } from "./helpers";

test("student journey covers dashboard, uploads, jobs, assessments, interviews, and learning", async ({ browser }, testInfo) => {
  const { page, context } = await signIn(browser, {
    email: "student1@spip.com",
    password: "Student@123",
  });

  try {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: /Overview/i })).toBeVisible();
    for (const item of ["Overview", "Job Discovery", "Mock Interviews", "Learning Paths", "Notifications", "Settings"]) {
      await expect(page.getByRole("link", { name: item })).toBeVisible();
    }
    await snapshot(page, testInfo, "student-dashboard");

    await page.goto("/dashboard/settings");
    await expect(page.getByRole("heading", { name: /Settings/i })).toBeVisible();
    await page.getByRole("tab", { name: "Resume & Documents" }).click();
    await page.locator("#resume-upload").setInputFiles(fixtures().resumePdf);
    await expect(page.getByText(/Resume uploaded successfully/i)).toBeVisible({ timeout: 30000 });
    await page.getByRole("tab", { name: "Profile Details" }).click();
    await page.locator("#profile-picture-upload").setInputFiles(fixtures().profilePng);
    await expect(page.locator('img[alt="Profile"]')).toHaveAttribute("src", /\/uploads\/profile\//, { timeout: 30000 });
    await snapshot(page, testInfo, "student-settings");

    await page.goto("/dashboard/jobs");
    await expect(page.getByRole("heading", { name: /Job Discovery/i })).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(/AI Job Assistant/i)).toBeVisible();
    await expect(page.getByText(/Filters/i)).toBeVisible();
    await page.getByLabel(/Remote only/i).check();
    await expect(page.getByText(/Freshness unknown/i).first()).toBeVisible();
    await snapshot(page, testInfo, "student-jobs");

    await page.goto("/dashboard/assessments");
    await expect(page.getByRole("heading", { name: /Assessments/i })).toBeVisible({ timeout: 30000 });
    await page.getByRole("link", { name: /Start Assessment/i }).first().click();
    await expect(page.getByRole("button", { name: /Enter Fullscreen to Start/i })).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /Enter Fullscreen to Start/i }).click();
    await expect(page.getByText(/Question 1 of/i)).toBeVisible({ timeout: 30000 });
    await page.locator("div.cursor-pointer").first().click();
    await page.getByRole("button", { name: /Submit Test/i }).click();
    await expect(page).toHaveURL(/\/dashboard\/assessments\/\d+\/result/);
    await expect(page.getByText(/Assessment Completed!/i)).toBeVisible();
    await snapshot(page, testInfo, "student-assessment-result");

    await page.goto("/dashboard/interviews");
    await expect(page.getByText(/AI Interview Platform/i)).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /New Interview/i }).click();
    await page.getByRole("button", { name: /Coding Interview/i }).click();
    const interviewForm = page.locator("aside form");
    await interviewForm.locator("input").nth(0).fill("Sprint 15 QA Coding");
    await interviewForm.locator("input").nth(1).fill("SPIP");
    await interviewForm.locator("input").nth(2).fill("Frontend Engineer");
    await page.getByRole("button", { name: /Start Interview/i }).click();
    await expect(page).toHaveURL(/\/dashboard\/interviews\/\d+\/live/);
    await expect(page.getByText(/Pre-interview check/i)).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /Test camera/i }).click();
    await page.getByRole("button", { name: /Test microphone/i }).click();
    await page.getByRole("checkbox", { name: /I understand the proctoring rules and the interview flow/i }).check();
    await expect(page.getByRole("button", { name: /Enter Fullscreen to Start/i })).toBeEnabled({ timeout: 30000 });
    await page.getByRole("button", { name: /Enter Fullscreen to Start/i }).click();
    await expect(page.getByText(/Code editor/i)).toBeVisible({ timeout: 30000 });
    await page.locator("select").selectOption("java");
    await page.locator('textarea[aria-label="Code mirror fallback"]').fill('class Main { public static void main(String[] args) { System.out.print("OK"); } }');
    await page.getByRole("button", { name: /^Run$/i }).click();
    await expect(page.locator("pre").first()).toContainText("OK", { timeout: 30000 });
    await page.getByRole("button", { name: /Submit solution/i }).click();
    await expect(page.locator("pre").first()).toContainText("Submitted to the interviewer for evaluation.", { timeout: 30000 });
    await snapshot(page, testInfo, "student-interview-live");

    await page.goto("/dashboard/learning");
    await expect(page.getByText(/Enterprise Learning Hub/i)).toBeVisible({ timeout: 30000 });
    await page.getByPlaceholder("Data Structures").fill("QA Roadmap");
    await page.getByPlaceholder("Computer Science").fill("Data Structures");
    await page.getByPlaceholder("Intermediate").fill("Intermediate");
    await page.getByPlaceholder("8").fill("6");
    await page.getByRole("button", { name: /Generate roadmap/i }).click();
    await page.waitForURL(/\/dashboard\/learning(\/module\/\d+)?/, { timeout: 30000 });
    if (new URL(page.url()).pathname === "/dashboard/learning") {
      await page.getByRole("button", { name: /^Open$/ }).first().click();
    }
    await expect(page).toHaveURL(/\/dashboard\/learning\/module\/\d+/);
    await expect(page.getByText(/Back to Learning Hub/i)).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("tab", { name: /Sources/i })).toBeVisible({ timeout: 30000 });
    await page.getByRole("tab", { name: /Sources/i }).click();
    await page.getByRole("button", { name: /Summary/i }).click();
    await page.getByRole("button", { name: /Quiz/i }).click();
    await page.getByRole("button", { name: "Flashcards", exact: true }).click();
    await expect(page.getByRole("tab", { name: /Practice Quiz/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Flashcards/i })).toBeVisible();
    await expect(page.getByRole("tab", { name: /Revision Notes/i })).toBeVisible();
    await snapshot(page, testInfo, "student-learning-module");

    await page.goto("/dashboard/learning");
    await page.getByPlaceholder("Trees and Graphs").fill("QA Revision Session");
    await page.getByPlaceholder("Algorithms").fill("Algorithms");
    await page.getByRole("button", { name: /Start study session/i }).click();
    await expect(page).toHaveURL(/\/dashboard\/learning\/chat\/\d+/);
    await expect(page.getByText(/study assistant/i)).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /Summary/i }).click();
    await expect(page.getByRole("heading", { name: /summary/i })).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /Quiz/i }).click();
    await expect(page.getByRole("heading", { name: "Practice Quiz" })).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: /Flashcards/i }).click();
    await expect(page.getByRole("heading", { name: "Flashcards", exact: true }).first()).toBeVisible({ timeout: 30000 });
    await snapshot(page, testInfo, "student-learning-chat");
  } finally {
    await context.close();
  }
});
