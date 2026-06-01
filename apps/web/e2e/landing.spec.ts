/**
 * E2E: Landing page
 *
 * Verifies the unauthenticated home page renders correctly and
 * provides a sign-in CTA.
 *
 * Auth: no Clerk session required (public route).
 */

import { test, expect } from '@playwright/test';
import { goto } from './helpers';

test.describe('Landing page', () => {
  test('renders the ClinicalScribe heading', async ({ page }) => {
    await goto(page, '/');
    await expect(page.getByRole('heading', { name: 'ClinicalScribe' })).toBeVisible();
  });

  test('shows the synthetic-data disclaimer', async ({ page }) => {
    await goto(page, '/');
    await expect(page.getByText(/not for clinical use/i)).toBeVisible();
  });

  test('sign-in link navigates to /sign-in', async ({ page }) => {
    await goto(page, '/');
    const signInLink = page.getByRole('link', { name: /sign in/i });
    await expect(signInLink).toBeVisible();
    await expect(signInLink).toHaveAttribute('href', '/sign-in');
  });

  test('unauthenticated /encounters redirects to /sign-in', async ({ page }) => {
    await page.goto('/encounters');
    await page.waitForURL(/sign-in/);
    expect(page.url()).toContain('sign-in');
  });
});
