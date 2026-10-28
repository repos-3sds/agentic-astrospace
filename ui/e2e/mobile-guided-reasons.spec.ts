import { expect, Route, test } from '@playwright/test';

/**
 * Guided answers carry no chart terms in the prose. Each statement that rests
 * on a chart factor ends with a small numbered chip; tapping it opens that
 * factor (the matching `technical_basis` item) under the paragraph, and
 * tapping again closes it. Screenshots in light and dark for the review.
 */
const profile = {
  id: 'a', name: 'Kavya', relation: 'self',
  birth_year: 1997, birth_month: 6, birth_day: 26, birth_hour: 9,
  birth_minute: 15, birth_city: 'Hyderabad', birth_nation: 'IN',
};
const reading = {
  acknowledgment: 'You asked when you can start earning.',
  technical_basis: [
    { factor: 'Jupiter, your career guide, is weak in Capricorn', reading: 'Effort pays off slowly; early offers may undervalue you.', source: 'houses' },
    { factor: 'Moon sub-period, 16 Oct 2026 to 5 Jan 2027', reading: 'A short window that favours home-based or flexible work.', source: 'dasha_relevance' },
    { factor: 'Saturn crossing the 10th from the Moon', reading: 'Work asks for patience and routine more than quick wins.', source: 'transits' },
  ],
  interpretation: 'Earning is possible, but it will come through steady, patient steps rather than a sudden break [1].\n\n' +
    'The weeks from mid-October to early January are your best opening this season, especially for work you can do from home or on flexible hours [2]. ' +
    'Expect a slow start and keep going even if the first replies are quiet [3].',
  summary_and_assurance: 'You can begin small this winter and grow from there.',
  guidance: { practical_actions: ['Pick one skill you already have and offer it to two people you know.'], remedies: [], follow_up_questions: [] },
  confidence: 'medium',
};
const thread = {
  id: '9a1b2c3d-0000-4000-8000-000000000011', kundli_id: 'a', title: 'Start earning', message_count: 2,
  created_at: '2026-10-28T04:00:00Z', last_message_at: '2026-10-28T04:00:00Z', archived_at: null,
};

for (const scheme of ['light', 'dark'] as const) {
  test(`guided reason chips open the chart factor (${scheme})`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-chrome-360', 'One phone project covers this screen');
    await page.setViewportSize({ width: 375, height: 812 });
    await page.emulateMedia({ colorScheme: scheme });
    await page.route('**/api/v1/**', async (route: Route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === '/api/v1/auth/config') return route.fulfill({ json: { enabled: false } });
      if (path === '/api/v1/kundlis') return route.fulfill({ json: [profile] });
      if (path === `/api/v1/ask/threads/${thread.id}`) return route.fulfill({ json: { thread, messages: [
        { id: 'q-1', role: 'user', content: 'When can she start earning money?', created_at: thread.created_at },
        { id: '9a1b2c3d-0000-4000-8000-000000000012', role: 'assistant', content: reading.interpretation,
          domain: 'career', evidence: { structured_reading: reading, schema_version: 'ask_structured_v1' },
          created_at: thread.created_at },
      ] } });
      return route.fulfill({ status: 503, json: { detail: `Unmocked ${path}` } });
    });
    await page.addInitScript(() => {
      localStorage.setItem('astrospace.activeKundliId', 'a');
      localStorage.setItem('astrospace-preferences', JSON.stringify({ experienceMode: 'guided', language: 'en' }));
    });
    await page.goto(`/m/ask/answer?thread=${thread.id}`);

    const card = page.getByLabel('Plain guidance');
    await expect(card).toBeVisible();
    await expect(card).not.toContainText('[1]');
    await expect(page.getByText('Tap a number to see the chart reason')).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`guided-chips-${scheme}.png`), animations: 'disabled' });

    const chip = page.getByRole('button', { name: 'Chart reason 2' });
    await chip.click();
    await expect(chip).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByRole('note')).toContainText('Moon sub-period, 16 Oct 2026 to 5 Jan 2027');
    await page.screenshot({ path: testInfo.outputPath(`guided-chip-open-${scheme}.png`), animations: 'disabled' });

    await chip.click();
    await expect(page.getByRole('note')).toHaveCount(0);
  });
}
