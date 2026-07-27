import { expect, test } from '@playwright/test';

const modes = [
  {
    id: 'guided',
    tabs: ['Today', 'Ask', 'What to do', 'Calendar', 'More'],
    insight: 'A SIMPLE START',
  },
  {
    id: 'balanced',
    tabs: ['Today', 'Ask', 'Chart', 'Calendar', 'More'],
    insight: 'WHY THIS IS PERSONAL',
  },
  {
    id: 'practitioner',
    tabs: ['Today', 'Chart', 'Periods', 'Transits', 'More'],
    insight: 'WORKBENCH READY',
  },
] as const;

test.describe('mobile persona presentation contracts', () => {
  test.skip(({ browserName }) => browserName !== 'chromium');

  for (const mode of modes) {
    test(`${mode.id} keeps shared truth while adapting the journey`, async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.route('**/api/v1/**', async (route) => {
        const path = new URL(route.request().url()).pathname;
        if (path === '/api/v1/auth/config') {
          await route.fulfill({ json: { enabled: false } });
        } else if (path === '/api/v1/kundlis') {
          await route.fulfill({ json: [] });
        } else {
          await route.fulfill({ status: 503, json: { detail: 'Not needed by persona contract' } });
        }
      });
      await page.addInitScript((experienceMode) => {
        localStorage.setItem('astrospace-preferences', JSON.stringify({
          chartStyle: 'south',
          ayanamsha: 'lahiri',
          nodeType: 'mean',
          timezoneMode: 'browser',
          panchangaPlace: null,
          language: 'en',
          regionalFormat: 'en-IN',
          experienceMode,
          tone: experienceMode === 'practitioner' ? 'direct' : 'gentle',
        }));
      }, mode.id);

      await page.goto('/m/insight');
      await expect(page.getByText(mode.insight)).toBeVisible();
      await page.screenshot({ path: `/tmp/astrospace-persona-${mode.id}.png`, fullPage: true });

      await page.goto('/m/today');
      await page.locator('nav[aria-label="Primary"]').waitFor();
      const labels = await page.locator('nav[aria-label="Primary"] .label').allTextContents();
      expect(labels).toEqual(mode.tabs);
      await expect(page.getByText('Create your first chart')).toBeVisible();
    });
  }
});
