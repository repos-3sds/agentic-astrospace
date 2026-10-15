import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';

import { environment } from '../../environments/environment';
import { AnalyticsService, screenName } from './analytics.service';
import { PreferencesService } from './preferences.service';

describe('AnalyticsService', () => {
  const shareUsage = signal(true);
  let fetchSpy: jasmine.Spy;
  const original = environment.posthog;

  beforeEach(() => {
    shareUsage.set(true);
    environment.posthog = { key: 'phc_test', host: 'https://eu.i.posthog.com' };
    fetchSpy = spyOn(window, 'fetch').and.resolveTo(new Response('{}'));
    TestBed.configureTestingModule({
      providers: [{ provide: PreferencesService, useValue: { shareUsage, experienceMode: signal('balanced') } }],
    });
  });

  afterEach(() => { environment.posthog = original; });

  const sent = () => JSON.parse(fetchSpy.calls.mostRecent().args[1].body as string);

  it('sends a batch with an anonymous id and no person profile', () => {
    const analytics = TestBed.inject(AnalyticsService);
    analytics.track('ask_answered', { domain: 'career' });
    analytics.flush();
    expect(fetchSpy.calls.mostRecent().args[0]).toBe('https://eu.i.posthog.com/batch/');
    const body = sent();
    expect(body.api_key).toBe('phc_test');
    expect(body.batch[0].event).toBe('ask_answered');
    expect(body.batch[0].properties.domain).toBe('career');
    expect(body.batch[0].properties.$process_person_profile).toBeFalse();
    expect(body.batch[0].properties.distinct_id).toMatch(/^[0-9a-f-]{36}$/);
  });

  it('sends nothing when the reader turns sharing off, and drops what was queued', () => {
    const analytics = TestBed.inject(AnalyticsService);
    analytics.track('why_opened');
    shareUsage.set(false);
    analytics.flush();
    analytics.track('why_opened');
    analytics.flush();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('sends nothing without a configured key', () => {
    environment.posthog = { key: '' };
    const analytics = TestBed.inject(AnalyticsService);
    analytics.captureException(new Error('boom'));
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('reports a crash at once, with ids and emails scrubbed', () => {
    const analytics = TestBed.inject(AnalyticsService);
    analytics.captureException(new Error('Profile 3f2b1c9e-1d2e-4f5a-9b8c-7d6e5f4a3b2c for a@b.com failed'));
    const props = sent().batch[0].properties;
    expect(sent().batch[0].event).toBe('$exception');
    expect(props.$exception_message).toBe('Profile :id for :email failed');
    expect(fetchSpy.calls.mostRecent().args[1].keepalive).toBeTrue();
  });

  it('strips ids and query strings from screen names', () => {
    expect(screenName('/m/settings/profiles/3f2b1c9e-1d2e-4f5a-9b8c-7d6e5f4a3b2c/edit?x=1')).toBe('/m/settings/profiles/:id/edit');
    expect(screenName('/m/compat/results?partner=abc')).toBe('/m/compat/results');
  });
});
