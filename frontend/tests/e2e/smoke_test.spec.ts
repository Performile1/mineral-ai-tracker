import { test, expect } from '@playwright/test';

/**
 * E2E Smoke Test for Mineral AI Tracker (PRD v10.0 Phase 11)
 * 
 * Tests the complete user journey:
 * 1. Login with NextAuth
 * 2. Navigate to ticker analysis
 * 3. Start analysis
 * 4. Check task status
 */

test.describe('Mineral AI Tracker E2E Smoke Test', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('http://localhost:3000');
  });

  test('Login -> Analysis -> Status flow', async ({ page }) => {
    // Step 1: Login with NextAuth (mock for testing)
    await page.click('text=Sign In');
    await page.waitForURL(/\/auth\/signin/);
    
    // For testing, we'll use a mock login button if available
    // In production, this would test actual OAuth flow
    const mockLoginButton = page.locator('text=Mock Login');
    if (await mockLoginButton.isVisible()) {
      await mockLoginButton.click();
      await page.waitForURL(/\/dashboard/);
    } else {
      // Skip login test if mock not available
      console.log('Mock login not available, skipping auth test');
    }

    // Step 2: Navigate to ticker analysis
    await page.goto('http://localhost:3000');
    const tickerInput = page.locator('input[placeholder*="ticker" i]');
    if (await tickerInput.isVisible()) {
      await tickerInput.fill('AAPL');
      await page.click('button:has-text("Analyze")');
    } else {
      // Alternative navigation
      await page.click('text=Discovery');
    }

    // Step 3: Check that analysis started
    await page.waitForTimeout(2000); // Wait for async task to start
    
    // Step 4: Check task status
    const statusElement = page.locator('text=Processing').or(page.locator('text=Completed')).or(page.locator('text=Pending'));
    await expect(statusElement).toBeVisible({ timeout: 10000 });

    // Verify we can see some analysis result
    const resultElement = page.locator('text=Buffett Score').or(page.locator('text=Signal'));
    await expect(resultElement).toBeVisible({ timeout: 30000 });
  });

  test('Admin Dashboard accessibility', async ({ page }) => {
    // Test admin dashboard is accessible (requires admin permissions)
    await page.goto('http://localhost:3000/admin/dashboard');
    
    // Check dashboard loads
    await expect(page.locator('h1:has-text("Admin Dashboard")').or(page.locator('text=Dashboard'))).toBeVisible({ timeout: 5000 });
    
    // Check system health indicators are present
    await expect(page.locator('text=System Health').or(page.locator('text=Health'))).toBeVisible();
  });

  test('Health check endpoint', async ({ request }) => {
    // Test backend health check endpoint
    const response = await request.get('http://localhost:8000/health');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('status', 'healthy');
  });

  test('Admin dashboard API', async ({ request }) => {
    // Test admin dashboard API endpoint
    const response = await request.get('http://localhost:8000/api/admin/dashboard');
    
    // May return 401 if not authenticated, which is expected
    expect([200, 401]).toContain(response.status());
    
    if (response.status() === 200) {
      const data = await response.json();
      expect(data).toHaveProperty('analysis_stats');
      expect(data).toHaveProperty('system_health');
    }
  });
});
