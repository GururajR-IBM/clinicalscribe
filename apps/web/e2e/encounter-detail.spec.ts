/**
 * E2E: Encounter detail page
 *
 * Verifies the SOAP card renders when an encounter is in "complete" state,
 * and that the audio dropzone is shown for "pending" encounters.
 *
 * All API calls are intercepted — no live gateway required.
 */

import { test, expect } from '@playwright/test';
import { mockGateway } from './helpers';

test.describe('Encounter detail — complete state', () => {
  test.beforeEach(async ({ page }) => {
    await mockGateway(page);
  });

  test('renders the SOAP card sections', async ({ page }) => {
    await page.goto('/encounters/enc-test-001');
    if (page.url().includes('sign-in')) {
      test.skip();
      return;
    }

    // SOAP card headings
    for (const section of ['Subjective', 'Objective', 'Assessment', 'Plan']) {
      await expect(page.getByText(section)).toBeVisible({ timeout: 5000 });
    }
  });

  test('shows the synthetic-data disclaimer in SOAP card', async ({ page }) => {
    await page.goto('/encounters/enc-test-001');
    if (page.url().includes('sign-in')) {
      test.skip();
      return;
    }
    await expect(page.getByText(/not for clinical use/i).first()).toBeVisible();
  });

  test('shows the Complete status badge', async ({ page }) => {
    await page.goto('/encounters/enc-test-001');
    if (page.url().includes('sign-in')) {
      test.skip();
      return;
    }
    await expect(page.getByText('Complete')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Encounter detail — pending state (audio upload)', () => {
  test('shows audio dropzone when upload URL is in localStorage', async ({ page }) => {
    // Inject upload URL into localStorage before navigation
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('upload_url_enc-pending-001', 'http://localhost:9999/fake-sas-url');
    });

    // Override the encounter detail API to return pending state
    await page.route('**/encounters/enc-pending-001', (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          encounter_id: 'enc-pending-001',
          patient_id: 'PT-00999',
          status: 'pending',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          notes: null,
          soap_draft: null,
          error_message: null,
        }),
      });
    });

    await page.route('**/encounters/enc-pending-001/events', (route) => {
      return route.fulfill({ status: 200, contentType: 'text/event-stream', body: '' });
    });

    await page.goto('/encounters/enc-pending-001');
    if (page.url().includes('sign-in')) {
      test.skip();
      return;
    }

    await expect(page.getByText(/drop audio here/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/max 25 mb/i)).toBeVisible();
  });
});
