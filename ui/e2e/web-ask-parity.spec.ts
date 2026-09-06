import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const profile = (id: string) => ({
  id, name: id === 'a' ? 'Anika' : 'Ravi', relation: 'self',
  birth_year: 1990, birth_month: 1, birth_day: 1, birth_hour: 12,
  birth_minute: 0, birth_city: 'Mumbai', birth_nation: 'IN',
});
const reading = {
  acknowledgment: 'You are asking about a career change.',
  technical_basis: [{ factor: 'Career context', reading: 'Consider a measured transition.', source: 'houses' }],
  interpretation: 'Plan the transition carefully and compare the practical alternatives.',
  summary_and_assurance: 'Preparation gives you room to choose.',
  guidance: { practical_actions: ['Review your options.'], remedies: [], follow_up_questions: ['What should I study next?'] },
  confidence: 'medium',
};

for (const width of [1280, 390, 2560]) {
  test(`web Ask shares conversation, persona, history and memory at ${width}px`, async ({ context, page }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: 'http://127.0.0.1:4200' });
    await page.setViewportSize({ width, height: 900 });
    const requests: Record<string, unknown>[] = [];
    const memoryWrites: Record<string, unknown>[] = [];
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    const thread = { id: 'thread-a', kundli_id: 'a', title: 'Career change', message_count: 2, created_at: '2026-09-01T00:00:00Z', last_message_at: '2026-09-01T00:00:00Z', archived_at: null as string | null };
    await page.route('**/api/v1/**', async route => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname;
      if (path.endsWith('/auth/config')) return route.fulfill({ json: { enabled: false } });
      if (path.endsWith('/kundlis')) return route.fulfill({ json: [profile('a'), profile('b')] });
      if (path.endsWith('/stream')) {
        requests.push(request.postDataJSON());
        return route.fulfill({ contentType: 'text/event-stream', body:
          'data: ' + JSON.stringify({ type: 'status', stage: 'interpreting', label: 'Checking chart context' }) + '\n\n' +
          'data: ' + JSON.stringify({ type: 'done', status: 'answered', schema_version: 'ask_structured_v1', domain: 'career', reading, thread_id: 'thread-a', context_used: ['houses'], evidence_refs: ['houses'] }) + '\n\n' +
          'data: ' + JSON.stringify({ type: 'memory_candidate', profile_id: 'a', revision: 0, candidate: {
            key: 'employment_status', value: { code: 'retired' }, label: 'Employment', display_value: 'Retired',
            excerpt: 'I am retired', sensitivity: 'personal', requires_confirmation: true,
          } }) + '\n\n' });
      }
      if (path.endsWith('/ask/threads')) return route.fulfill({ json: { threads: (url.searchParams.get('archived') === 'true') === !!thread.archived_at ? [thread] : [] } });
      if (path.endsWith('/archive')) { thread.archived_at = '2026-09-04T00:00:00Z'; return route.fulfill({ json: {} }); }
      if (path.endsWith('/restore')) { thread.archived_at = null; return route.fulfill({ json: {} }); }
      if (path.endsWith('/ask/threads/thread-a')) return route.fulfill({ json: { thread, messages: [
        { id: 'user-1', role: 'user', content: 'Career change', created_at: thread.created_at },
        { id: 'answer-1', role: 'assistant', content: reading.interpretation, domain: 'career', evidence: { structured_reading: reading, schema_version: 'ask_structured_v1' }, created_at: thread.created_at },
      ] } });
      if (path.endsWith('/context')) return route.fulfill({ json: { profile_id: 'a', revision: 0, facts: [], contradictions: [], logical_constraints: [], status: 'ready' } });
      if (path.endsWith('/context/facts')) {
        memoryWrites.push(request.postDataJSON());
        return route.fulfill({ json: { revision: 1, fact: { id: 'fact-a', key: 'employment_status', value: { code: 'retired' }, supersedes_id: null } } });
      }
      if (path.includes('/admin/')) return route.fulfill({ status: 403, json: { detail: 'Not an administrator' } });
      return route.fulfill({ json: {} });
    });
    await page.addInitScript(() => {
      localStorage.setItem('astrospace.activeKundliId', 'b');
      localStorage.setItem('astrospace-preferences', JSON.stringify({ experienceMode: 'balanced', language: 'en', memoryEnabled: true, memoryMode: 'ask' }));
    });
    await page.goto('/kundli/a/ask');
    const host = page.locator('app-ask-tab');
    await expect(host.locator('as-ask-home')).toBeVisible();
    if (width >= 768) {
      const workspace = await host.boundingBox();
      const intro = await host.locator('.ask-hero').boundingBox();
      const input = await host.locator('as-ask-composer').boundingBox();
      expect(workspace!.width).toBeGreaterThan(width - 400);
      expect(input!.y - (intro!.y + intro!.height)).toBeLessThan(40);
      await expect(host.locator('as-ask-home .appbar')).toBeHidden();
    }
    await page.screenshot({ path: `/tmp/web-ask-home-${width}.png`, fullPage: true });
    await host.getByLabel('Reading style').selectOption('practitioner');
    await host.getByRole('textbox', { name: 'Your question' }).fill('I am retired. What career work could I explore?');
    await host.getByRole('button', { name: 'Send', exact: true }).click();
    await expect(host.getByText(reading.interpretation, { exact: true })).toBeVisible();
    expect(requests[0].experience_mode).toBe('practitioner');
    expect(requests[0].start_thread).toBe(true);
    await expect(page).toHaveURL(/\/kundli\/a\/ask\/answer\?thread=thread-a/);
    await expect(host.getByRole('region', { name: 'Save profile memory' })).toBeVisible();
    await host.getByRole('button', { name: 'Copy Answer', exact: true }).click();
    await expect(host.getByRole('button', { name: 'Copied', exact: true })).toBeVisible();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('SIDDHA · STRUCTURED READING');
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('PROVENANCE');
    const downloadPromise = page.waitForEvent('download');
    await host.getByRole('button', { name: 'Download PDF', exact: true }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/^siddha-career-\d{4}-\d{2}-\d{2}\.pdf$/);
    const downloadedPath = await download.path();
    expect(downloadedPath).not.toBeNull();
    const pdfHeader = readFileSync(downloadedPath!, { encoding: 'latin1' }).slice(0, 8);
    expect(pdfHeader.startsWith('%PDF-1.4')).toBe(true);
    expect(memoryWrites).toHaveLength(0);
    await host.getByRole('button', { name: 'Remember', exact: true }).click();
    await expect.poll(() => memoryWrites.length).toBe(1);
    await page.screenshot({ path: `/tmp/web-ask-answer-${width}.png`, fullPage: true });
    await page.evaluate(() => document.documentElement.classList.add('app-dark'));
    await expect(host.locator('.answer').last()).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
    await page.screenshot({ path: `/tmp/web-ask-answer-dark-${width}.png`, fullPage: true, animations: 'disabled' });
    await page.evaluate(() => document.documentElement.classList.remove('app-dark'));
    const composer = await host.locator('as-ask-composer').boundingBox();
    const bottomNav = await page.locator('.mobile-bottom-nav').boundingBox();
    if (bottomNav && composer) expect(composer.y + composer.height).toBeLessThanOrEqual(bottomNav.y);
    await host.getByRole('textbox').fill('And next year?');
    await host.getByRole('button', { name: 'Send', exact: true }).click();
    await expect.poll(() => requests.length).toBe(2);
    expect(requests[1].thread_id).toBe('thread-a');
    if (width <= 1100) await host.getByRole('button', { name: 'Toggle conversations' }).click();
    await host.getByRole('link', { name: 'History', exact: true }).click();
    await host.getByRole('button', { name: 'Conversation actions' }).click();
    await host.getByRole('button', { name: 'Archive', exact: true }).click();
    await host.getByRole('tab', { name: 'Archived', exact: true }).click();
    await host.getByRole('button', { name: /Career change/ }).click();
    await expect(host.getByRole('button', { name: 'Restore', exact: true })).toBeVisible();
    expect(requests.length).toBe(2);
    if (width <= 1100) await host.getByRole('button', { name: 'Toggle conversations' }).click();
    await host.getByRole('link', { name: 'Memory', exact: true }).click();
    await expect(host.getByRole('heading', { name: 'What Siddha remembers' })).toBeVisible();
    await expect(host.getByText('Nothing remembered yet')).toBeVisible();
    await page.screenshot({ path: `/tmp/web-ask-memory-${width}.png`, fullPage: true });
    await host.getByRole('link', { name: 'Back', exact: true }).click();
    await expect(page).toHaveURL(/\/kundli\/a\/ask$/);
    await host.getByRole('textbox', { name: 'Your question' }).fill('A new career question');
    await host.getByRole('button', { name: 'Send', exact: true }).click();
    await expect.poll(() => requests.length).toBe(3);
    expect(requests[2].start_thread).toBe(true);
    expect(requests[2].thread_id).toBeUndefined();
    await page.goto('/kundli/b/ask/answer?thread=thread-a');
    await expect(page).toHaveURL(/\/kundli\/b\/ask$/);
    await expect(host.getByText(reading.interpretation, { exact: true })).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}

test('mobile Ask shares the structured answer as a real Siddha PDF file', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => {
    localStorage.setItem('astrospace.activeKundliId', 'a');
    localStorage.setItem('astrospace-preferences', JSON.stringify({ experienceMode: 'balanced', language: 'en' }));
    Object.defineProperty(navigator, 'canShare', { configurable: true, value: () => true });
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: async (data: ShareData) => {
        const file = data.files?.[0];
        const header = file ? new TextDecoder().decode((await file.arrayBuffer()).slice(0, 8)) : '';
        (window as any).__sharedPdf = {
          title: data.title, text: data.text, name: file?.name, type: file?.type, header,
        };
      },
    });
  });
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/config')) return route.fulfill({ json: { enabled: false } });
    if (path.endsWith('/kundlis')) return route.fulfill({ json: [profile('a')] });
    if (path.endsWith('/stream')) return route.fulfill({
      contentType: 'text/event-stream',
      body: 'data: ' + JSON.stringify({
        type: 'done', status: 'answered', schema_version: 'ask_structured_v1', domain: 'career',
        reading, thread_id: 'thread-mobile', context_used: ['houses'], evidence_refs: ['houses'],
      }) + '\n\n',
    });
    return route.fulfill({ json: {} });
  });

  await page.goto('/m/ask/answer?q=When%20will%20my%20career%20settle%3F&pending=1');
  const answer = page.locator('as-ask-answer');
  await expect(answer.getByText(reading.interpretation, { exact: true })).toBeVisible();
  await answer.getByRole('button', { name: 'Share PDF', exact: true }).click();
  await expect.poll(() => page.evaluate(() => (window as any).__sharedPdf)).toMatchObject({
    title: 'Siddha reading for Anika',
    text: 'When will my career settle?',
    type: 'application/pdf',
    header: '%PDF-1.4',
  });
  const shared = await page.evaluate(() => (window as any).__sharedPdf);
  expect(shared.name).toMatch(/^siddha-career-\d{4}-\d{2}-\d{2}\.pdf$/);
  await page.screenshot({ path: '/tmp/mobile-ask-pdf-share.png', fullPage: true });
});

for (const surface of ['web', 'mobile']) {
  for (const boundary of [
    { event: { type: 'fatal_error', message: 'Could not finish this reading.' }, text: 'Could not finish this reading.' },
    { event: { type: 'context_unavailable', retryable: true }, text: 'I could not check your saved profile context just now' },
  ]) {
    test(`${surface} renders ${boundary.event.type} without a false answer`, async ({ page }) => {
      let calls = 0;
      await page.route('**/api/v1/**', async route => {
        const path = new URL(route.request().url()).pathname;
        if (path.endsWith('/auth/config')) return route.fulfill({ json: { enabled: false } });
        if (path.endsWith('/kundlis')) return route.fulfill({ json: [profile('a')] });
        if (path.endsWith('/stream')) {
          calls += 1;
          return route.fulfill({ contentType: 'text/event-stream', body: 'data: ' + JSON.stringify(boundary.event) + '\n\n' });
        }
        return route.fulfill({ json: {} });
      });
      const root = surface === 'web' ? '/kundli/a/ask' : '/m/ask';
      await page.goto(root + '/answer?q=Career%20question&pending=1');
      const answer = page.locator('as-ask-answer');
      await expect(answer.getByText(boundary.text, { exact: false })).toBeVisible();
      await expect(answer.getByRole('button', { name: 'Try again' })).toBeVisible();
      await expect(answer.getByRole('button', { name: 'Stop', exact: true })).toHaveCount(0);
      expect(calls).toBe(1);
      await answer.getByRole('link', { name: 'Back to Ask' }).click();
      await expect(page).toHaveURL(new RegExp(root + '$'));
    });
  }
}
