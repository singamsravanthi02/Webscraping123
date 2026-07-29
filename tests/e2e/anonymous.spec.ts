import { expect, test } from "@playwright/test";

test("anonymous flow covers the public and auth pages", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByText(/^SPIP$/i)).toBeVisible();
  await expect(page.getByText(/Sreyas AI Placement OS 2\.0 is now live/i)).toBeVisible();
  await expect(page.getByRole("link", { name: /Get Started/i })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("anonymous-home.png"), fullPage: true });

  await page.goto("/login");
  await expect(page.getByText(/Welcome back/i)).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByRole("button", { name: /Sign In/i })).toBeVisible();

  await page.goto("/register");
  await expect(page.getByText(/Create an account/i)).toBeVisible();
  await expect(page.getByLabel("Full Name")).toBeVisible();
  await expect(page.getByRole("combobox")).toBeVisible();

  await page.goto("/forgot-password");
  await expect(page.getByText(/Password reset is disabled|Reset Password/i)).toBeVisible();

  await page.goto("/reset-password");
  await expect(page.getByText(/Password reset is disabled|Create New Password/i)).toBeVisible();

  await page.goto("/verify-email");
  await expect(page.getByText(/Email verification is disabled|Verify your email/i)).toBeVisible();
});
