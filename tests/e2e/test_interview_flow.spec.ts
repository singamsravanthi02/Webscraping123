import { test, expect } from '@playwright/test';

test.describe('Enterprise AI Interview Flow', () => {
  test('Complete end-to-end HR interview flow', async ({ page, context }) => {
    // Grant microphone and camera permissions
    await context.grantPermissions(['microphone', 'camera']);
    
    // Login flow
    await page.goto('/login');
    await page.fill('input[name="email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'Password123!');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
    
    // Navigate to Interviews
    await page.click('text="Interviews"');
    await page.waitForURL('/dashboard/interviews');
    
    // Start a new HR Mock Interview
    await page.click('button:has-text("New Mock Interview")');
    await page.fill('input[placeholder*="Job title"]', 'Frontend Developer');
    await page.click('button:has-text("Start Interview")');
    
    // Wait for redirect to live interview preflight
    await page.waitForURL(/\/dashboard\/interviews\/\d+\/live/);
    
    // Preflight checks
    await page.click('text="Test camera"');
    await page.waitForSelector('text="Camera is live."');
    
    await page.click('text="Test microphone"');
    await page.waitForSelector('text="Microphone permission is ready."');
    
    await page.check('input[type="checkbox"]'); // Accept rules
    
    // Start Interview
    await page.click('button:has-text("Enter Fullscreen to Start")');
    
    // Active Phase
    // Verify UI Layout
    await expect(page.locator('text="AI Interviewer"')).toBeVisible();
    await expect(page.locator('text="You"')).toBeVisible(); // Camera label
    
    // Wait for the first question to appear
    await expect(page.locator('text="Text Fallback"')).toBeVisible();
    
    // Answer the first question using text fallback
    await page.fill('textarea[placeholder*="Type your answer"]', 'I am very excited about this frontend developer role because I love React.');
    await page.click('button:has-text("Submit Answer")');
    
    // Wait for the AI to respond (another question)
    // The textarea should be cleared after submit, and re-enabled once AI responds
    await expect(page.locator('textarea[placeholder*="Type your answer"]')).toHaveValue('');
    
    // Ensure we can end the interview
    page.on('dialog', dialog => dialog.accept());
    await page.click('button[title="End Interview"]');
    
    // Wait for report generation page or redirect to result
    await page.waitForURL(/\/dashboard\/interviews\/\d+\/result/);
    
    // On the result page, wait for processing to finish
    await expect(page.locator('text="Interview Evaluation Report"')).toBeVisible({ timeout: 15000 });
    
    // Verify evaluation metrics are visible
    await expect(page.locator('text="Overall Grade"')).toBeVisible();
    await expect(page.locator('text="Technical Depth"')).toBeVisible();
    await expect(page.locator('text="Communication"')).toBeVisible();
  });
});
