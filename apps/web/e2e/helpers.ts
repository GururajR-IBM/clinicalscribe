/**
 * Shared Playwright helpers for ClinicalScribe E2E tests.
 *
 * Auth: Clerk test-mode uses signed cookies set by the test setup fixture.
 * Gateway: tests use a mock server unless PLAYWRIGHT_REAL_GATEWAY=true.
 */

import { type Page } from '@playwright/test';

/** Navigate to the app and wait for the page to be interactive. */
export async function goto(page: Page, path: string = '/') {
  await page.goto(path);
  await page.waitForLoadState('networkidle');
}

/** Stub the gateway API endpoints with deterministic mock responses. */
export async function mockGateway(page: Page) {
  // POST /encounters → create response
  await page.route('**/encounters', (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          encounter_id: 'enc-test-001',
          upload_url: 'http://localhost:9999/fake-blob-upload',
          upload_expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
          status: 'pending',
        }),
      });
    }
    // GET /encounters → list
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          encounter_id: 'enc-test-001',
          patient_id: 'PT-00123',
          status: 'complete',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          notes: null,
          soap_draft: {
            subjective: 'Patient reports 3-day productive cough and low-grade fever.',
            objective: 'Temperature 38.1°C, SpO2 96% on room air.',
            assessment: 'Community-acquired pneumonia (J18.9).',
            plan: 'Amoxicillin 500 mg TID for 7 days. Follow-up in 1 week.',
          },
          error_message: null,
        },
      ]),
    });
  });

  // GET /encounters/:id → detail
  await page.route('**/encounters/enc-test-001', (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        encounter_id: 'enc-test-001',
        patient_id: 'PT-00123',
        status: 'complete',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        notes: null,
        soap_draft: {
          subjective: 'Patient reports 3-day productive cough and low-grade fever.',
          objective: 'Temperature 38.1°C, SpO2 96% on room air.',
          assessment: 'Community-acquired pneumonia (J18.9).',
          plan: 'Amoxicillin 500 mg TID for 7 days. Follow-up in 1 week.',
        },
        error_message: null,
      }),
    });
  });

  // SSE events stream → empty (no active stream needed for static tests)
  await page.route('**/encounters/*/events', (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: '',
    });
  });

  // Blob upload URL (fake)
  await page.route('http://localhost:9999/**', (route) => {
    return route.fulfill({ status: 201, body: '' });
  });
}
