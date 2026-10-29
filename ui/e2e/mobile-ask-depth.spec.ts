import { expect, Route, test } from '@playwright/test';

/**
 * Fast / Deep in the Ask box (Hawk, 2026-10-28: "like Claude's thinking
 * mode"). The Deep chip sends depth=deep with the question and is remembered.
 * Screenshots of Ask home with Deep off and on, light and dark.
 */
const profile = {
  id: 'a', name: 'Kavya', relation: 'self',
  birth_year: 1997, birth_month: 6, birth_day: 26, birth_hour: 9,
  birth_minute: 15, birth_city: 'Hyderabad', birth_nation: 'IN',
};

for (const scheme of ['light', 'dark'] as const) {
  test(`deep switch in the Ask box (${scheme})`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-chrome-360', 'One phone project covers this screen');
    await page.emulateMedia({ colorScheme: scheme });
    const sent: Record<string, unknown>[] = [];
    await page.route('**/api/v1/**', async (route: Route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === '/api/v1/auth/config') return route.fulfill({ json: { enabled: false } });
      if (path === '/api/v1/kundlis') return route.fulfill({ json: [profile] });
      if (path === '/api/v1/ask/a/stream') {
        sent.push(route.request().postDataJSON());
        await new Promise((resolve) => setTimeout(resolve, 6000));
        return route.fulfill({ status: 503, json: { detail: 'not in this test' } }).catch(() => undefined);
      }
      return route.fulfill({ status: 503, json: { detail: `Unmocked ${path}` } });
    });
    await page.addInitScript(() => localStorage.setItem('astrospace.activeKundliId', 'a'));
    await page.goto('/m/ask');

    const chip = page.getByRole('button', { name: /Deep answer/ });
    await expect(chip).toHaveAttribute('aria-pressed', 'false');
    await page.screenshot({ path: `test-results/ask-depth/fast-${scheme}.png` });

    // The "+" menu: ask about someone, add a family member, Deep answer.
    await page.getByRole('button', { name: 'Ask options' }).click();
    await expect(page.getByRole('menuitem', { name: /Ask about someone/ })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: /Add a family member/ })).toBeVisible();
    const deepItem = page.getByRole('menuitemcheckbox', { name: /Deep answer/ });
    await deepItem.click();
    await expect(deepItem).toHaveAttribute('aria-checked', 'true');
    await page.screenshot({ path: `test-results/ask-depth/menu-${scheme}.png` });
    await page.keyboard.press('Escape');
    await expect(chip).toHaveAttribute('aria-pressed', 'true');

    // The person chip opens the profile switcher.
    await page.getByRole('button', { name: /Asking about Kavya/ }).click();
    await expect(page.getByRole('heading', { name: 'Switch profile' })).toBeVisible();
    await page.screenshot({ path: `test-results/ask-depth/person-${scheme}.png` });
    await page.locator('.profile-row').first().click();
    await expect(page.getByRole('heading', { name: 'Switch profile' })).toBeHidden();
    await page.screenshot({ path: `test-results/ask-depth/deep-empty-${scheme}.png` });
    await page.locator('as-ask-composer input.field').fill('Will my YouTube channel grow?');
    await page.screenshot({ path: `test-results/ask-depth/deep-${scheme}.png` });

    await page.getByRole('button', { name: 'Send' }).first().click();
    // First question on this phone: the AI-sharing notice holds it until agreed.
    await expect(page.getByRole('heading', { name: 'Answers are written with AI' })).toBeVisible();
    expect(sent.length).toBe(0);
    await page.screenshot({ path: `test-results/ask-depth/ai-sharing-${scheme}.png` });
    await page.getByRole('button', { name: 'Agree and ask' }).click();
    await expect.poll(() => sent.length).toBeGreaterThan(0);
    expect(sent[0]['depth']).toBe('deep');
    await expect(page.getByText('Deep reading · about a minute')).toBeVisible();
    await expect(page.locator('.deep-tag')).toBeVisible();
    await page.screenshot({ path: `test-results/ask-depth/deep-waiting-${scheme}.png` });

    await page.reload();
    await expect(page.getByRole('button', { name: /Deep answer/ })).toHaveAttribute('aria-pressed', 'true');
  });
}
