import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";

const chromePath = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";

export default defineConfig({
  testDir: "../tests/e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { outputFolder: "../playwright-report", open: "never" }]],
  retries: 0,
  timeout: 120000,
  expect: { timeout: 20000 },
  use: {
    baseURL: process.env.E2E_WEB_URL || "http://localhost:3000",
    viewport: { width: 1440, height: 1080 },
    screenshot: "only-on-failure",
    video: "on",
    trace: "on",
    launchOptions: existsSync(chromePath) ? { executablePath: chromePath } : {},
  },
});
