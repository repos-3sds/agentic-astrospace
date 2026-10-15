import { expect, test } from '@playwright/test';

const profile = {
  id: 'a', name: 'Anika', relation: 'self',
  birth_year: 1990, birth_month: 1, birth_day: 1, birth_hour: 12,
  birth_minute: 0, birth_city: 'Mumbai', birth_nation: 'IN',
};

test('mobile muhurta renders an excluded intent as a refer-out card, not a failure', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => {
    localStorage.setItem('astrospace.activeKundliId', 'a');
    localStorage.setItem('astrospace-preferences', JSON.stringify({ experienceMode: 'balanced', language: 'en' }));
  });
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/config')) return route.fulfill({ json: { enabled: false } });
    if (path.endsWith('/kundlis')) return route.fulfill({ json: [profile] });
    if (path.includes('/muhurta/')) {
      return route.fulfill({
        status: 422,
        json: { detail: { kind: 'refer_out', domain: 'health', message: 'We don\'t pick times for health decisions.' } },
      });
    }
    return route.fulfill({ json: {} });
  });

  await page.goto('/m/muhurta/results?goal=surgery_date&range=month');
  const card = page.locator('.refer-out');
  await expect(card).toBeVisible();
  await expect(card).toContainText('Not something we time');
  await expect(card).toContainText('We don\'t pick times for health decisions.');
  await expect(card.getByRole('link', { name: 'Choose another goal' })).toBeVisible();
  // A refusal by design must not look like an outage: no retry control.
  await expect(page.locator('as-generic-error')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /try again|retry/i })).toHaveCount(0);
});
