import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for ClinicalScribe E2E tests.
 *
 * Runs against the Next.js dev server (started automatically).
 * Set PLAYWRIGHT_BASE_URL to override for staging/production tests.
 *
 * Gateway stub: tests that require API calls use MSW to mock the gateway.
 * Clerk auth: CLERK_USER_ID env var enables the Clerk test mode bypass.
 */
export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/results',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ['html', { outputFolder: './e2e/report', open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: {
      // Clerk test-mode bypass — set CLERK_SECRET_KEY to a test key in CI
      NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? 'pk_test_placeholder',
      CLERK_SECRET_KEY: process.env.CLERK_SECRET_KEY ?? 'sk_test_placeholder',
      NEXT_PUBLIC_GATEWAY_URL: process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8000',
    },
  },
});
