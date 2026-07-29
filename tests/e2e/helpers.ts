import { expect, type Browser, type Page, type TestInfo } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const WEB_URL = process.env.E2E_WEB_URL || "http://localhost:3000";

type Credentials = {
  email: string;
  password: string;
};

type Fixtures = {
  resumePdf: string;
  knowledgeTxt: string;
  profilePng: string;
};

let fixtureCache: Fixtures | null = null;

async function completeOnboarding(page: Page) {
  await expect(page.getByLabel("Phone Number")).toBeVisible({ timeout: 30000 });
  await page.getByLabel("Phone Number").fill("+919876543210");
  await page.getByRole("button", { name: /Next Step/i }).click();
  await page.getByLabel("College\/Institute Name").fill("Sreyas Institute of Engineering and Technology");
  await page.getByLabel("Department").fill("Engineering");
  await page.getByLabel("Branch\/Major").fill("Computer Science");
  await page.getByLabel("Current Semester").fill("6");
  await page.getByLabel("CGPA").fill("8.5");
  await page.getByRole("button", { name: /Next Step/i }).click();
  await page.getByLabel("Technical Skills (comma separated)").fill("JavaScript, React, Testing");
  await page.getByLabel("Career Goal").fill("Placement officer focused on student success and hiring outcomes.");
  await page.getByRole("button", { name: /Next Step/i }).click();
  await page.locator("#file-upload").setInputFiles(fixtures().resumePdf);
  await page.getByRole("button", { name: /Complete Profile/i }).click();
}

export function fixtures() {
  if (fixtureCache) return fixtureCache;

  const dir = join(tmpdir(), "spip-e2e-fixtures");
  mkdirSync(dir, { recursive: true });
  const stamp = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;

  const resumePdf = join(dir, "resume.pdf");
  if (!existsSync(resumePdf)) {
    const script = [
      "import os",
      "from pypdf import PdfWriter",
      "out = os.environ['OUT']",
      "writer = PdfWriter()",
      "writer.add_blank_page(width=200, height=200)",
      "with open(out, 'wb') as handle:",
      "    writer.write(handle)",
    ].join("\n");
    execFileSync("python", ["-c", script], {
      env: { ...process.env, OUT: resumePdf },
      stdio: "ignore",
    });
  }

  const knowledgeTxt = join(dir, `knowledge-${stamp}.txt`);
  writeFileSync(
    knowledgeTxt,
    [
      "SPIP QA knowledge note",
      "Roadmap, interview, job, and learning regression fixture.",
      `Run stamp: ${new Date().toISOString()}`,
    ].join("\n"),
    "utf8"
  );

  const profilePng = join(dir, "profile.png");
  if (!existsSync(profilePng)) {
    writeFileSync(
      profilePng,
      Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2d3WcAAAAASUVORK5CYII=", "base64")
    );
  }

  fixtureCache = { resumePdf, knowledgeTxt, profilePng };
  return fixtureCache;
}

export async function signIn(browser: Browser, { email, password }: Credentials) {
  const context = await browser.newContext({
    baseURL: WEB_URL,
    acceptDownloads: true,
    permissions: ["camera", "microphone"],
  });
  const page = await context.newPage();

  await page.goto("/login");
  await expect(page.getByText(/Welcome back/i)).toBeVisible();
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /Sign In/i }).click();
  await page.waitForFunction(
    () => window.location.pathname.startsWith("/dashboard") || window.location.pathname.startsWith("/onboarding"),
    undefined,
    { timeout: 60000 }
  );
  if (new URL(page.url()).pathname.startsWith("/onboarding")) {
    await completeOnboarding(page);
    await page.waitForFunction(() => window.location.pathname.startsWith("/dashboard"), undefined, { timeout: 60000 });
  }
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible({ timeout: 30000 });

  return { page, context };
}

export async function signUpPlacementOfficer(browser: Browser, { email, password }: Credentials) {
  const context = await browser.newContext({
    baseURL: WEB_URL,
    acceptDownloads: true,
    permissions: ["camera", "microphone"],
  });
  const page = await context.newPage();

  await page.goto("/register");
  await expect(page.getByText(/Create an account/i)).toBeVisible();
  await page.locator("#fullName").fill("Placement QA");
  await page.locator("#email").fill(email);
  await page.getByRole("combobox").click();
  await page.getByRole("option", { name: /Placement Officer/i }).click();
  await page.locator("#password").fill(password);
  await page.locator("#confirmPassword").fill(password);
  await page.getByRole("checkbox", { name: /I accept the Terms of Service/i }).check();
  await page.getByRole("button", { name: /Create Account/i }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/login");
  await expect(page.getByText(/Welcome back/i)).toBeVisible();
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: /Sign In/i }).click();
  await page.waitForFunction(
    () => window.location.pathname.startsWith("/dashboard") || window.location.pathname.startsWith("/onboarding"),
    undefined,
    { timeout: 60000 }
  );
  if (new URL(page.url()).pathname.startsWith("/onboarding")) {
    await completeOnboarding(page);
    await page.waitForFunction(() => window.location.pathname.startsWith("/dashboard"), undefined, { timeout: 60000 });
  }
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible({ timeout: 30000 });

  return { page, context };
}

export async function snapshot(page: Page, testInfo: TestInfo, name: string) {
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`), fullPage: true });
}
