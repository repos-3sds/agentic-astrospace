import { expect, test } from '@playwright/test';

const modes = [
  {
    id: 'guided',
    tabs: ['Today', 'Ask', 'Calendar', 'More'],
    insight: 'YOUR JOURNEY BEGINS',
    insightCta: 'Continue to Today',
  },
  {
    id: 'balanced',
    tabs: ['Today', 'Ask', 'Calendar', 'More'],
    insight: 'YOUR JOURNEY BEGINS',
    insightCta: 'Continue to Today',
  },
  {
    id: 'practitioner',
    tabs: ['Today', 'Yantra', 'Dashas', 'Calendar', 'More'],
    insight: 'KUNDLI CALCULATION',
    insightCta: 'Open Practitioner Workbench',
  },
] as const;

/**
 * The first-insight screen computes from the active profile's chart, so the
 * persona-specific variant only renders once a profile exists. The profile is
 * withdrawn again before Today so the empty state stays part of the contract.
 */
const profile = {
  id: 'persona-profile',
  name: 'Persona Test',
  relation: 'self',
  birth_year: 1990,
  birth_month: 4,
  birth_day: 12,
  birth_hour: 6,
  birth_minute: 30,
  birth_city: 'Chennai',
  birth_nation: 'IN',
  sun_sign: 'Aries',
  moon_sign: 'Taurus',
  ascendant: 'Cancer',
};

test.describe('mobile persona presentation contracts', () => {
  test.skip(({ browserName }) => browserName !== 'chromium');

  for (const mode of modes) {
    test(`${mode.id} keeps shared truth while adapting the journey`, async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });
      let profiles: Record<string, unknown>[] = [profile];
      await page.route('**/api/v1/**', async (route) => {
        const path = new URL(route.request().url()).pathname;
        if (path === '/api/v1/auth/config') {
          await route.fulfill({ json: { enabled: false } });
        } else if (path === '/api/v1/kundlis') {
          await route.fulfill({ json: profiles });
        } else if (path === `/api/v1/vedic/${profile.id}/all`) {
          await route.fulfill({ json: {
            meta: { ayanamsha: { name: 'Lahiri' } },
            provenance: { house_system: 'Whole-Sign', timezone: 'Asia/Kolkata' },
            planets: {
              Sun: { sign: 'Aries', house: 10, dms: '28°14′', nakshatra: 'Krittika', nakshatra_pada: 1 },
              Moon: { sign: 'Taurus', house: 11, dms: '12°40′', nakshatra: 'Rohini', nakshatra_pada: 2 },
            },
            shadbala: { classical: { ranking: [{ planet: 'Sun', total: 426 }] } },
            dashas: { current: { mahadasha: { lord: 'Moon' }, antardasha: { lord: 'Saturn' } } },
          } });
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
      await expect(page.getByRole('link', { name: mode.insightCta })).toBeVisible();
      await page.screenshot({ path: `/tmp/astrospace-persona-${mode.id}.png`, fullPage: true });

      profiles = [];
      await page.goto('/m/today');
      await page.locator('nav[aria-label="Primary"]').waitFor();
      const labels = await page.locator('nav[aria-label="Primary"] .label').allTextContents();
      expect(labels).toEqual(mode.tabs);
      await expect(page.getByText('Create your first chart')).toBeVisible();
    });
  }
});
