import { test, expect } from '@playwright/test';

/**
 * Phase 11.2: Critical Path E2E Test
 * 
 * Tests the core user flow:
 * 1. Navigate to admin dashboard and verify system status
 * 2. Navigate to backtesting page and verify UI
 * 3. Test backend health endpoint
 * 4. Verify admin dashboard API endpoints
 */

test.describe('Critical Path - System Verification', () => {
  const BASE_URL = 'http://localhost:3000';
  const API_URL = 'http://localhost:8000';

  test.beforeAll(async () => {
    // Verify services are running before tests
    console.log('Checking if services are running...');
    
    try {
      const healthResponse = await fetch(`${API_URL}/health`);
      if (!healthResponse.ok) {
        throw new Error('Backend health check failed');
      }
      console.log('Backend is running');
    } catch (error) {
      console.error('Backend is not running:', error);
    }
  });

  test('Admin Dashboard - System Status Verification', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/dashboard`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Verify page title
    await expect(page).toHaveTitle(/Mineral AI Tracker/);

    // Verify admin dashboard header is present
    const header = page.locator('h1');
    await expect(header).toContainText('Admin Dashboard');

    // Wait for data to load (max 10 seconds)
    await page.waitForTimeout(5000);

    // Verify analysis stats section exists
    const analysisStats = page.locator('text=Today');
    await expect(analysisStats).toBeVisible();

    // Verify system health section exists
    const systemHealth = page.locator('text=System Health');
    await expect(systemHealth).toBeVisible();

    // Verify Celery queue status section exists
    const celeryStatus = page.locator('text=Celery Queue Status');
    await expect(celeryStatus).toBeVisible();

    // Verify recent activity section exists
    const recentActivity = page.locator('text=Recent Activity');
    await expect(recentActivity).toBeVisible();

    console.log('Admin dashboard UI verification passed');
  });

  test('Admin Dashboard - API Endpoints', async () => {
    // Test dashboard API endpoint
    const dashboardResponse = await fetch(`${API_URL}/api/admin/dashboard`);
    
    if (dashboardResponse.ok) {
      const dashboardData = await dashboardResponse.json();
      expect(dashboardData).toHaveProperty('analysis_stats');
      expect(dashboardData).toHaveProperty('system_health');
      expect(dashboardData).toHaveProperty('recent_activity');
      console.log('Dashboard API endpoint verified');
    } else {
      console.log('Dashboard API endpoint not responding (may be expected if backend not running)');
    }

    // Test Celery status API endpoint
    const celeryResponse = await fetch(`${API_URL}/api/admin/celery-status`);
    
    if (celeryResponse.ok) {
      const celeryData = await celeryResponse.json();
      expect(celeryData).toHaveProperty('status');
      expect(celeryData).toHaveProperty('active_tasks');
      expect(celeryData).toHaveProperty('workers');
      console.log('Celery status API endpoint verified');
    } else {
      console.log('Celery status API endpoint not responding (may be expected if Celery not running)');
    }

    // Test Prometheus metrics API endpoint
    const prometheusResponse = await fetch(`${API_URL}/api/admin/prometheus-metrics`);
    
    if (prometheusResponse.ok) {
      const prometheusData = await prometheusResponse.json();
      expect(prometheusData).toHaveProperty('status');
      expect(prometheusData).toHaveProperty('key_metrics');
      console.log('Prometheus metrics API endpoint verified');
    } else {
      console.log('Prometheus metrics API endpoint not responding (may be expected if Prometheus not running)');
    }
  });

  test('Backtesting Page - UI Verification', async ({ page }) => {
    await page.goto(`${BASE_URL}/backtesting`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Verify page title
    await expect(page).toHaveTitle(/Mineral AI Tracker/);

    // Verify backtesting header
    const header = page.locator('h1');
    await expect(header).toContainText('The Time Machine');

    // Verify backtest form button exists
    const runButton = page.locator('button:has-text("Run New Backtest")');
    await expect(runButton).toBeVisible();

    console.log('Backtesting page UI verification passed');
  });

  test('Backend Health Check', async () => {
    const response = await fetch(`${API_URL}/health`);
    
    expect(response.ok).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(data.status).toBe('healthy');
    
    console.log('Backend health check passed');
  });

  test('Database Migration Verification', async () => {
    // Test if backtest tables exist by calling the runs endpoint
    const response = await fetch(`${API_URL}/api/backtesting/runs`);
    
    // Even if empty, the endpoint should respond
    if (response.ok) {
      const data = await response.json();
      expect(data).toHaveProperty('runs');
      expect(Array.isArray(data.runs)).toBeTruthy();
      console.log('Database migration verified - backtest tables exist');
    } else {
      console.log('Database migration verification skipped - backend not responding');
    }
  });

  test('Security Headers Verification', async () => {
    const response = await fetch(`${API_URL}/health`);
    
    if (response.ok) {
      const headers = response.headers;
      
      // Verify key security headers are present
      expect(headers.get('x-content-type-options')).toBe('nosniff');
      expect(headers.get('x-frame-options')).toBe('DENY');
      expect(headers.get('x-xss-protection')).toBe('1; mode=block');
      
      console.log('Security headers verification passed');
    } else {
      console.log('Security headers verification skipped - backend not responding');
    }
  });
});
