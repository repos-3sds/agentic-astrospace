import { expect, test } from '@playwright/test';

/**
 * The Settings tab after Deepak's review (2026-10-28): Account card first,
 * rows set once folded into two pages, Terms and Privacy as footer links.
 */

const profiles = [
  { id: 'a', name: 'Anika', relation: 'self', birth_year: 1990, birth_month: 3, birth_day: 14, birth_hour: 6, birth_minute: 20, birth_city: 'Pune', birth_nation: 'IN' },
  { id: 'b', name: 'Ravi', relation: 'father', birth_year: 1960, birth_month: 7, birth_day: 2, birth_hour: 9, birth_minute: 0, birth_city: 'Pune', birth_nation: 'IN' },
];

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => {
    localStorage.setItem('astrospace.activeKundliId', 'b');
    localStorage.setItem('astrospace-preferences', JSON.stringify({ experienceMode: 'balanced', language: 'en' }));
  });
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/config')) return route.fulfill({ json: { enabled: false } });
    if (path.endsWith('/kundlis')) return route.fulfill({ json: profiles });
    if (path.endsWith('/entitlements')) return route.fulfill({ json: { access_tier: 'plus', features: {}, limits: {}, usage: {} } });
    if (path.includes('/panchanga') || path.includes('subhashita')) return route.fulfill({ status: 404, json: {} });
    return route.fulfill({ json: {} });
  });
});

test('Settings leads with Account and keeps legal links in the footer', async ({ page }) => {
  await page.goto('/m/settings');
  const card = page.getByRole('link', { name: 'Account' });
  await expect(card).toContainText('Plus');
  // The holder's name, not the person being viewed (Ravi is selected).
  await expect(card).toContainText('Anika');
  await expect(card).not.toContainText('Ravi');

  const eyebrows = page.locator('h2.eyebrow');
  await expect(eyebrows).toHaveText(['YOU AND YOUR FAMILY', 'ALERTS', 'READINGS', 'APP']);
  for (const gone of ['Manage profiles', 'Chart method', 'Light or dark', 'Terms of Service', 'Privacy Policy']) {
    await expect(page.getByText(gone, { exact: true })).toHaveCount(0);
  }
  await expect(page.locator('.legal-foot button')).toHaveText(['Terms', 'Privacy']);

  // My birth details edits the reader's own profile, not the one being viewed.
  const mine = page.getByRole('link', { name: /My birth details/ });
  await expect(mine).toHaveAttribute('href', '/m/settings/profiles/a/edit');
  await expect(mine).toContainText('14 Mar 1990 · Pune');

  await card.click();
  await expect(page).toHaveURL(/\/m\/settings\/account$/);
  await expect(page.locator('.action-label').first()).toContainText('Plan and purchases');
});

test('rows set once live one level down', async ({ page }) => {
  await page.goto('/m/settings');
  await page.getByRole('link', { name: /Astrology preferences/ }).click();
  await expect(page).toHaveURL(/\/m\/settings\/astrology$/);
  await expect(page.locator('.row-label')).toHaveText(['City for timings', 'Festivals to show', 'Chart method']);

  await page.goto('/m/settings/look');
  await expect(page.locator('.row-label')).toContainText(['Light or dark', 'Language and voice', 'Vibration']);
});

test('an older account with no "self" row names its first profile', async ({ page }) => {
  // Hawk's own profile was saved as "relative" by an older build.
  const older = [
    { ...profiles[1], relation: 'relative', created_at: '2026-09-01T00:00:00Z' },
    { ...profiles[0], name: 'Kiran', relation: 'relative', created_at: '2026-08-01T00:00:00Z' },
  ];
  await page.route('**/api/v1/kundlis', (route) => route.fulfill({ json: older }));
  await page.goto('/m/settings');
  await expect(page.getByRole('link', { name: 'Account' })).toContainText('Kiran');
  await expect(page.getByRole('link', { name: /My birth details/ })).toHaveAttribute('href', '/m/settings/profiles/a/edit');
});
