import { expect, test, type Page, type Route } from '@playwright/test';

// Several people for one purpose: the Muhurta "Who else is taking part?"
// picker, who each time suits, and "Ask about people together" in Ask.

const base = {
  birth_month: 1, birth_day: 1, birth_hour: 12, birth_minute: 0,
  birth_city: 'Hyderabad', birth_nation: 'IN', birth_time_accuracy: 'exact',
};
const profiles = [
  { ...base, id: 'r', name: 'Ramesh K', relation: 'self', birth_year: 1974 },
  { ...base, id: 'l', name: 'Lakshmi', relation: 'spouse', birth_year: 1978 },
  { ...base, id: 'a', name: 'Arjun', relation: 'child', birth_year: 2002 },
];

const slot = (date: string, people: { name: string; standing: string }[]) => ({
  date, window: 'morning', start: '07:12', end: '08:40',
  start_iso: `${date}T07:12:00+05:30`, end_iso: `${date}T08:40:00+05:30`,
  trimmed: false, duration_minutes: 88, score: 80, quality: 'good', label: 'Good',
  why: { supports: ['Good tarabala for all of you'], against: [] },
  vara: 'Thursday', nakshatra: 'Rohini', people,
});

async function mock(page: Page, seen: { muhurta?: URL; ask?: unknown }) {
  await page.addInitScript(() => {
    localStorage.setItem('astrospace.activeKundliId', 'r');
    localStorage.setItem('astrospace-preferences', JSON.stringify({ experienceMode: 'balanced', language: 'en' }));
  });
  await page.route('**/api/v1/**', async (route: Route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/auth/config')) return route.fulfill({ json: { enabled: false } });
    if (url.pathname.endsWith('/kundlis')) return route.fulfill({ json: profiles });
    if (url.pathname.includes('/muhurta/')) {
      seen.muhurta = url;
      return route.fulfill({
        json: {
          results: [
            slot('2026-11-12', [{ name: 'you', standing: 'strong' }, { name: 'Lakshmi', standing: 'strong' },
              { name: 'Arjun', standing: 'fair' }]),
            slot('2026-11-19', [{ name: 'you', standing: 'strong' }, { name: 'Lakshmi', standing: 'fair' },
              { name: 'Arjun', standing: 'weak' }]),
          ],
          notes: [], disclaimer: 'Traditional guidance.', is_convention_dependent: true,
          observance_note: 'Tarabala counted from each person\'s birth star.',
        },
      });
    }
    if (url.pathname.includes('/ask')) seen.ask = route.request().postDataJSON();
    return route.fulfill({ status: 503, json: { detail: `Unmocked ${url.pathname}` } });
  });
}

for (const scheme of ['light', 'dark'] as const) {
  test(`muhurta checks a family together (${scheme})`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-chrome-360', 'One phone project covers this');
    await page.emulateMedia({ colorScheme: scheme });
    const seen: { muhurta?: URL } = {};
    await mock(page, seen);

    await page.goto('/m/muhurta?goal=griha_pravesha');
    const panel = page.getByRole('group', { name: 'Who else is taking part?' });
    await expect(panel).toBeVisible();
    await panel.getByRole('button', { name: 'Lakshmi' }).click();
    await panel.getByRole('button', { name: 'Arjun' }).click();
    await expect(panel.getByRole('button', { name: 'Lakshmi' })).toHaveAttribute('aria-pressed', 'true');
    await panel.scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath(`muhurta-with-${scheme}.png`) });

    await page.goto('/m/muhurta/results?goal=griha_pravesha&range=month&with=l,a');
    await expect(page.getByText('Good for Ramesh and Lakshmi · Fair for Arjun')).toBeVisible();
    expect(seen.muhurta?.searchParams.get('with_ids')).toBe('l,a');
    await page.screenshot({ path: testInfo.outputPath(`muhurta-results-${scheme}.png`) });
  });

  test(`ask picks people together (${scheme})`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-chrome-360', 'One phone project covers this');
    await page.emulateMedia({ colorScheme: scheme });
    await mock(page, {});
    await page.goto('/m/ask');
    await page.getByRole('button', { name: 'Ask options' }).click();
    await page.getByRole('menuitem', { name: /Ask about people together/ }).click();
    const dialog = page.getByRole('dialog', { name: 'Who else is this about?' });
    await dialog.getByRole('checkbox', { name: /Lakshmi/ }).click();
    await expect(dialog.getByRole('checkbox', { name: /Lakshmi/ })).toHaveAttribute('aria-checked', 'true');
    await page.screenshot({ path: testInfo.outputPath(`ask-together-dialog-${scheme}.png`) });
    await dialog.getByRole('button', { name: 'Done' }).click();
    await expect(page.getByRole('button', { name: 'Together with Lakshmi. Change' })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`ask-together-chip-${scheme}.png`) });
  });
}
