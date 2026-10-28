import { expect, Page, test } from '@playwright/test';

/**
 * Settings switches must change only the one tapped, and stay put, even when
 * the server is slow (Cloud Run + a far database answers a PUT in 1-2 s).
 * Deepak's report, 2026-10-28: tapping one email switch made others flip
 * off and back on by themselves, and on Panchang alarms the rows jumped.
 */

const profile = {
  id: 'a', name: 'Anika', relation: 'self',
  birth_year: 1990, birth_month: 1, birth_day: 1, birth_hour: 12,
  birth_minute: 0, birth_city: 'Mumbai', birth_nation: 'IN',
};

const CATEGORIES = ['daily_email', 'festival_email', 'weekly_email', 'monthly_email', 'lessons_email', 'tips_email'];

async function boot(page: Page, serverDelayMs: number): Promise<Record<string, boolean>> {
  const server: Record<string, boolean> = Object.fromEntries(CATEGORIES.map((c) => [c, false]));
  const state = () => ({ address: 'me@example.com', deliverable: true, suppressed_reason: null, categories: { ...server } });
  await page.addInitScript(() => {
    localStorage.setItem('astrospace.activeKundliId', 'a');
    localStorage.setItem('astrospace-preferences', JSON.stringify({ experienceMode: 'balanced', language: 'en' }));
  });
  await page.route('**/api/v1/**', async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    if (path.endsWith('/auth/config')) return route.fulfill({ json: { enabled: false } });
    if (path.endsWith('/kundlis')) return route.fulfill({ json: [profile] });
    if (path.includes('/panchanga') || path.includes('subhashita')) return route.fulfill({ status: 404, json: {} });
    if (path.endsWith('/me/email') && req.method() === 'GET') return route.fulfill({ json: state() });
    const put = path.match(/\/me\/email\/(\w+)$/);
    if (put && req.method() === 'PUT') {
      // The server writes at once and answers late, like production.
      server[put[1]] = (req.postDataJSON() as { enabled: boolean }).enabled;
      const answer = state();
      await new Promise((r) => setTimeout(r, serverDelayMs));
      return route.fulfill({ json: answer });
    }
    return route.fulfill({ json: {} });
  });
  return server;
}

async function emailStates(page: Page): Promise<boolean[]> {
  return page.locator('.switch[aria-label$=" by email"]').evaluateAll((els) =>
    els.map((el) => el.getAttribute('aria-checked') === 'true'),
  );
}

test('email switches: each tap changes only its own switch, with a slow server', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const server = await boot(page, 1500);
  await page.goto('/m/settings/notifications');
  const switches = page.locator('.switch[aria-label$=" by email"]');
  await expect(switches).toHaveCount(6);

  // Record every state the screen shows, so a flip that comes back is caught.
  await page.evaluate(() => {
    (window as unknown as { seen: string[] }).seen = [];
    const read = () => [...document.querySelectorAll('.switch[aria-label$=" by email"]')]
      .map((el) => (el.getAttribute('aria-checked') === 'true' ? '1' : '0')).join('');
    new MutationObserver(() => (window as unknown as { seen: string[] }).seen.push(read()))
      .observe(document.body, { subtree: true, attributes: true, attributeFilter: ['aria-checked'] });
  });

  // One at a time, a person's pace: well inside one server answer.
  for (const index of [0, 1, 2, 3]) {
    await switches.nth(index).click();
    await page.waitForTimeout(400);
  }
  // Saves go one at a time, so the server catches up after the screen does.
  await expect.poll(() => Object.values(server), { timeout: 10_000 }).toEqual([true, true, true, true, false, false]);

  const seen = await page.evaluate(() => (window as unknown as { seen: string[] }).seen);
  // Every state seen only ever adds the next switch: never one going back.
  for (let i = 1; i < seen.length; i += 1) {
    const before = seen[i - 1];
    const after = seen[i];
    for (let k = 0; k < 6; k += 1) {
      expect(before[k] === '1' && after[k] === '0', `switch ${k} flipped back: ${seen.join(' → ')}`).toBe(false);
    }
  }
  expect(await emailStates(page)).toEqual([true, true, true, true, false, false]);
});

test('panchang alarms: a switch changes only itself and no row moves', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await boot(page, 0);
  await page.goto('/m/settings/alarms');
  const switches = page.locator('.alarm-head .switch');
  await expect(switches).toHaveCount(12);
  const read = () => switches.evaluateAll((els) => els.map((el) => (el.getAttribute('aria-checked') === 'true' ? '1' : '0')).join(''));
  const tops = () => switches.evaluateAll((els) => els.map((el) => Math.round(el.getBoundingClientRect().top + window.scrollY)));

  const before = await tops();
  expect(await read()).toBe('001000100000');
  // Each click returns before the screen re-renders: wait for the switch's
  // own state, never read the row right after the tap.
  for (const index of [1, 3, 4]) {
    await switches.nth(index).click();
    await expect(switches.nth(index)).toHaveAttribute('aria-checked', 'true');
  }
  expect(await read()).toBe('011110100000');
  // Turning one on used to open its editor and push every row below down.
  expect(await tops()).toEqual(before);
});
