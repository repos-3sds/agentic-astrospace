import { expect, Route, test } from '@playwright/test';

/**
 * "Report this answer" on Ask (Google Play's rule for apps with AI-generated
 * content): every finished answer has the link, the sheet asks for a reason
 * and an optional note, and the report reaches the server with the answer the
 * reader saw. Screenshots in light and dark for the review.
 */
const profile = {
  id: 'a', name: 'Anika', relation: 'self',
  birth_year: 1990, birth_month: 1, birth_day: 1, birth_hour: 12,
  birth_minute: 0, birth_city: 'Mumbai', birth_nation: 'IN',
};
const reading = {
  acknowledgment: 'You are asking about a career change.',
  technical_basis: [{ factor: 'Career context', reading: 'Consider a measured transition.', source: 'houses' }],
  interpretation: 'Plan the move carefully. The next few months favour steady work over a sudden jump.',
  summary_and_assurance: 'Preparing now gives you room to choose.',
  guidance: { practical_actions: ['List two or three real options.'], remedies: [], follow_up_questions: ['Which month is best?'] },
  confidence: 'medium',
};
const thread = {
  id: '9a1b2c3d-0000-4000-8000-000000000001', kundli_id: 'a', title: 'Career change', message_count: 2,
  created_at: '2026-10-20T04:00:00Z', last_message_at: '2026-10-20T04:00:00Z', archived_at: null,
};

for (const scheme of ['light', 'dark'] as const) {
  test(`an answer can be reported (${scheme})`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-chrome-360', 'One phone project covers this screen');
    await page.setViewportSize({ width: 375, height: 812 });
    await page.emulateMedia({ colorScheme: scheme });
    const reports: Record<string, unknown>[] = [];
    await page.route('**/api/v1/**', async (route: Route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      if (path === '/api/v1/auth/config') return route.fulfill({ json: { enabled: false } });
      if (path === '/api/v1/kundlis') return route.fulfill({ json: [profile] });
      if (path === '/api/v1/ask/reports') {
        reports.push(route.request().postDataJSON());
        return route.fulfill({ status: 201, json: { id: 'r1', received: true } });
      }
      if (path === `/api/v1/ask/threads/${thread.id}`) return route.fulfill({ json: { thread, messages: [
        { id: 'q-1', role: 'user', content: 'Should I change my job this year?', created_at: thread.created_at },
        { id: '9a1b2c3d-0000-4000-8000-000000000002', role: 'assistant', content: reading.interpretation,
          domain: 'career', evidence: { structured_reading: reading, schema_version: 'ask_structured_v1' },
          created_at: thread.created_at },
      ] } });
      return route.fulfill({ status: 503, json: { detail: `Unmocked ${path}` } });
    });
    await page.addInitScript(() => {
      localStorage.setItem('astrospace.activeKundliId', 'a');
      localStorage.setItem('astrospace-preferences', JSON.stringify({ experienceMode: 'balanced', language: 'en' }));
    });
    await page.goto(`/m/ask/answer?thread=${thread.id}`);
    const link = page.getByRole('button', { name: 'Report this answer' });
    await link.scrollIntoViewIfNeeded();
    await expect(link).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`report-link-${scheme}.png`), animations: 'disabled' });

    await link.click();
    const sheet = page.getByRole('dialog', { name: 'Report this answer' });
    await expect(sheet).toBeVisible();
    await expect(sheet.getByRole('button', { name: 'Send report' })).toBeDisabled();
    await sheet.getByRole('radio', { name: /Wrong or made up/ }).click();
    await sheet.getByRole('textbox').fill('My chart has Saturn in the 10th, not the 8th.');
    await page.waitForTimeout(400);
    await page.screenshot({ path: testInfo.outputPath(`report-sheet-${scheme}.png`), animations: 'disabled' });

    await sheet.getByRole('button', { name: 'Send report' }).click();
    await expect(page.getByRole('heading', { name: 'Thank you' })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`report-sent-${scheme}.png`), animations: 'disabled' });
    expect(reports).toHaveLength(1);
    expect(reports[0]).toEqual(expect.objectContaining({
      reason: 'wrong', note: 'My chart has Saturn in the 10th, not the 8th.',
      question: 'Should I change my job this year?', thread_id: thread.id,
      message_id: '9a1b2c3d-0000-4000-8000-000000000002', experience_mode: 'balanced', language: 'en',
    }));
    expect(String(reports[0]['answer'])).toContain('Plan the move carefully');

    await page.getByRole('button', { name: 'Done' }).click();
    await expect(page.getByText('Reported. Thank you.')).toBeVisible();
  });
}
