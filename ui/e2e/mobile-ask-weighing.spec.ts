import { expect, Route, test } from '@playwright/test';

/**
 * Tool-using Ask judges every point of view, gives each a weight, and
 * combines them into one call. "How we weighed it" shows that under the
 * answer: plain names in Guided, astrology names and reasons in Balanced.
 * Screenshots in light and dark for the review.
 */
const profile = {
  id: 'a', name: 'Kavya', relation: 'self',
  birth_year: 1997, birth_month: 6, birth_day: 26, birth_hour: 9,
  birth_minute: 15, birth_city: 'Hyderabad', birth_nation: 'IN',
};
const reading = {
  acknowledgment: 'You asked if the Lilliput channel will grow.',
  technical_basis: [
    { factor: 'Jupiter period runs the 10th lord', reading: 'Steady growth through work done in public.', source: 'dasha_relevance' },
  ],
  interpretation: 'The channel can grow, slowly and with steady effort [1].',
  summary_and_assurance: 'Keep posting on a fixed day; growth comes in small steps.',
  guidance: { practical_actions: ['Post one video every week on the same day.'], remedies: [], follow_up_questions: [] },
  confidence: 'medium',
};
const weighing = {
  angles: [
    { key: 'lagna_houses', label: 'Lagna and houses', plain_label: 'Your rising sign and life areas', call: 'good', weight: 4, why: '10th lord Mercury in the 11th with Venus.' },
    { key: 'dignity_strength', label: 'Planet strength', plain_label: 'Strength of the key planets', call: 'moderate', weight: 4, why: 'Mercury in a friend sign, Shadbala average.' },
    { key: 'dasha', label: 'Dasha periods', plain_label: 'Your current time period', call: 'good', weight: 4, why: 'Jupiter mahadasha, Jupiter aspects the 10th.' },
    { key: 'varga', label: 'Divisional charts', plain_label: 'Deeper chart layers', call: 'neutral', weight: 3, why: 'D10 lagna lord in a neutral sign.' },
    { key: 'moon_sun_view', label: 'From Moon and Sun', plain_label: 'Your mind and self-confidence', call: 'moderate', weight: 3, why: '10th from Moon has Venus.' },
    { key: 'yogas_doshas', label: 'Yogas and doshas', plain_label: 'Special chart combinations', call: 'good', weight: 3, why: 'Dhana yoga holds; no blocking dosha.' },
    { key: 'jaimini', label: 'Jaimini', plain_label: 'A second way of reading the chart', call: 'neutral', weight: 2, why: 'Amatyakaraka Mars in a neutral house.' },
    { key: 'transits', label: 'Transits', plain_label: 'Where the planets are now', call: 'mixed', weight: 2, why: 'Saturn over the 10th from Moon slows results.' },
    { key: 'ashtakavarga', label: 'Ashtakavarga', plain_label: 'Planet support score', call: 'bad', weight: 2, why: 'Only 17 bindus in the 10th.' },
    { key: 'nakshatra', label: 'Nakshatra', plain_label: 'Your birth star', call: 'moderate', weight: 1, why: 'Hasta gives skill with hands and craft.' },
  ],
  overall: { score: 0.85, band: 'moderately good' },
};
const thread = {
  id: '9a1b2c3d-0000-4000-8000-000000000021', kundli_id: 'a', title: 'Lilliput channel', message_count: 2,
  created_at: '2026-10-28T04:00:00Z', last_message_at: '2026-10-28T04:00:00Z', archived_at: null,
};

for (const mode of ['guided', 'balanced'] as const) {
  for (const scheme of ['light', 'dark'] as const) {
    test(`how we weighed it card (${mode}, ${scheme})`, async ({ page }, testInfo) => {
      test.skip(testInfo.project.name !== 'mobile-chrome-360', 'One phone project covers this screen');
      await page.setViewportSize({ width: 375, height: 812 });
      await page.emulateMedia({ colorScheme: scheme });
      await page.route('**/api/v1/**', async (route: Route) => {
        const path = new URL(route.request().url()).pathname;
        if (path === '/api/v1/auth/config') return route.fulfill({ json: { enabled: false } });
        if (path === '/api/v1/kundlis') return route.fulfill({ json: [profile] });
        if (path === `/api/v1/ask/threads/${thread.id}`) return route.fulfill({ json: { thread, messages: [
          { id: 'q-1', role: 'user', content: 'Will her Lilliput YouTube channel grow?', created_at: thread.created_at },
          { id: '9a1b2c3d-0000-4000-8000-000000000022', role: 'assistant', content: reading.interpretation,
            domain: 'career', evidence: { structured_reading: reading, weighing, schema_version: 'ask_structured_v1' },
            created_at: thread.created_at },
        ] } });
        return route.fulfill({ status: 503, json: { detail: `Unmocked ${path}` } });
      });
      await page.addInitScript((m) => {
        localStorage.setItem('astrospace.activeKundliId', 'a');
        localStorage.setItem('astrospace-preferences', JSON.stringify({ experienceMode: m, language: 'en' }));
      }, mode);
      await page.goto(`/m/ask/answer?thread=${thread.id}`);

      const card = page.getByLabel('How we weighed it');
      await expect(card).toBeVisible();
      await expect(card.locator('.angle-row')).toHaveCount(10);
      await expect(card).toContainText('Moderately good');
      if (mode === 'guided') {
        await expect(card).toContainText('Your current time period');
        await expect(card).not.toContainText('Ashtakavarga');
        await expect(card).not.toContainText('bindus');
      } else {
        await expect(card).toContainText('Ashtakavarga');
        await expect(card).toContainText('Only 17 bindus in the 10th.');
      }
      await card.scrollIntoViewIfNeeded();
      await card.screenshot({ path: testInfo.outputPath(`weighing-${mode}-${scheme}.png`), animations: 'disabled' });
    });
  }
}
