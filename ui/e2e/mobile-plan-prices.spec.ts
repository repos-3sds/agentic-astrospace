import { expect, test } from '@playwright/test';

/**
 * Plans before the store answers (and on iPhone, until App Store purchases
 * exist): rupees on an Indian clock, dollars everywhere else. Testers in
 * Canada saw rupees on iPhone (2026-10-29).
 */

const products = [
  { id: 'siddha_plus_monthly', kind: 'plan', title: 'Plus, monthly', price_inr: 300, price_usd: 9.99, tier: 'plus', months: 1, questions: null },
  { id: 'siddha_practitioner_monthly', kind: 'plan', title: 'Practitioner, monthly', price_inr: 1000, price_usd: 24.99, tier: 'pro', months: 1, questions: null },
  { id: 'siddha_questions_1', kind: 'question_pack', title: '1 question', price_inr: 50, price_usd: 2.99, tier: null, months: null, questions: 1 },
  { id: 'siddha_questions_3', kind: 'question_pack', title: '3 questions', price_inr: 130, price_usd: 6.99, tier: null, months: null, questions: 3 },
];

const FREE = {
  account_id: 'account-1', access_tier: 'free', account_topology: 'individual',
  offer_code: null, status: 'free', source: 'free_default',
  effective_at: '2026-08-18T00:00:00', expires_at: null, grace_ends_at: null,
  revision: 0, catalog_revision: 2,
  entitlements: { 'ask.answers.period': 1, 'profiles.max': 1 },
  usage: {}, question_credits: 0, quotas_enforced: true,
};

async function openPlans(page: import('@playwright/test').Page): Promise<void> {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/config')) return route.fulfill({ json: { enabled: false } });
    if (path.endsWith('/entitlements/products')) return route.fulfill({ json: { products } });
    if (path.endsWith('/entitlements')) return route.fulfill({ json: FREE });
    if (path.endsWith('/kundlis')) return route.fulfill({ json: [] });
    return route.fulfill({ json: {} });
  });
  await page.goto('/m/subscription');
}

test.describe('in Canada', () => {
  test.use({ timezoneId: 'America/Toronto' });

  test('plans show dollars', async ({ page }) => {
    await openPlans(page);
    await expect(page.getByText('$9.99').first()).toBeVisible();
    await expect(page.getByText('$6.99').first()).toBeVisible();
    await expect(page.getByText(/₹/)).toHaveCount(0);
    await page.screenshot({ path: test.info().outputPath('plans-toronto.png'), fullPage: true });
    await page.getByRole('tab', { name: 'Practitioner' }).click();
    await expect(page.getByText('$24.99').first()).toBeVisible();
  });
});

test.describe('in India', () => {
  test.use({ timezoneId: 'Asia/Kolkata' });

  test('plans show rupees', async ({ page }) => {
    await openPlans(page);
    await expect(page.getByText('₹300').first()).toBeVisible();
    await expect(page.getByText('₹130').first()).toBeVisible();
    await expect(page.getByText(/\$\d/)).toHaveCount(0);
    await page.screenshot({ path: test.info().outputPath('plans-india.png'), fullPage: true });
    await page.getByRole('tab', { name: 'Practitioner' }).click();
    await expect(page.getByText('₹1,000').first()).toBeVisible();
  });
});
