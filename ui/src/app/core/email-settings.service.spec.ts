import { TestBed } from '@angular/core/testing';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import {
  EmailCategory,
  EmailSettingsService,
  EmailState,
} from './email-settings.service';

describe('EmailSettingsService', () => {
  let service: EmailSettingsService;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'put', 'post']);
    TestBed.configureTestingModule({
      providers: [
        EmailSettingsService,
        { provide: ApiService, useValue: api },
        { provide: AuthService, useValue: { isAuthenticated: () => true } },
      ],
    });
    service = TestBed.inject(EmailSettingsService);
  });

  it('asks the server to apply the sign-up defaults with the timezone', async () => {
    api.post.and.resolveTo({ address: 'a@b.c', deliverable: true, suppressed_reason: null, categories: {} });
    await service.applySignupDefaults();
    const [path, body] = api.post.calls.mostRecent().args as [string, { timezone: string; source: string }];
    expect(path).toBe('/me/email/defaults');
    expect(body.source).toBe('signup');
    expect(body.timezone).toBeTruthy();
  });

  it('never throws when the defaults call fails', async () => {
    api.post.and.rejectWith(new Error('offline'));
    await expectAsync(service.applySignupDefaults()).toBeResolved();
  });
  describe('switches tapped while the server is slow', () => {
    const CATS: EmailCategory[] = ['daily_email', 'festival_email', 'weekly_email', 'monthly_email', 'lessons_email', 'tips_email'];
    let server: Record<EmailCategory, boolean>;
    let answers: Array<() => void>;
    let fail: Set<EmailCategory>;

    const snapshot = (): EmailState => ({
      address: 'me@example.com', deliverable: true, suppressed_reason: null, categories: { ...server },
    });
    const shown = () => CATS.map((c) => (service.state()!.categories[c] ? '1' : '0')).join('');
    /** Lets the server answer everything it has been asked so far, one by one. */
    const answerAll = async () => {
      for (let i = 0; i < 20; i += 1) {
        await new Promise((r) => setTimeout(r));
        const next = answers.shift();
        if (next) next();
      }
      await new Promise((r) => setTimeout(r));
    };

    beforeEach(async () => {
      server = Object.fromEntries(CATS.map((c) => [c, false])) as Record<EmailCategory, boolean>;
      answers = [];
      fail = new Set();
      api.get.and.callFake(async () => snapshot() as never);
      api.put.and.callFake((path: string, body: unknown) => {
        const category = path.split('/').pop() as EmailCategory;
        return new Promise((resolve, reject) => {
          answers.push(() => {
            if (fail.has(category)) return reject(new Error('offline'));
            server[category] = (body as { enabled: boolean }).enabled;
            resolve(snapshot() as never);
          });
        }) as never;
      });
      await service.load();
    });

    it('never lets an answer flip back a switch tapped after it (Deepak, 2026-10-28)', async () => {
      const seen: string[] = [];
      void service.set('daily_email', true);
      seen.push(shown());
      void service.set('festival_email', true);
      seen.push(shown());
      void service.set('weekly_email', true);
      seen.push(shown());
      for (let i = 0; i < 3; i += 1) {
        await new Promise((r) => setTimeout(r));
        answers.shift()?.();
        await new Promise((r) => setTimeout(r));
        seen.push(shown());
      }
      await answerAll();
      expect(seen).toEqual(['100000', '110000', '111000', '111000', '111000', '111000']);
      expect(server.daily_email && server.festival_email && server.weekly_email).toBeTrue();
    });

    it('sends one call at a time, in the order tapped', async () => {
      void service.set('daily_email', true);
      void service.set('tips_email', true);
      await new Promise((r) => setTimeout(r));
      expect(api.put).toHaveBeenCalledTimes(1);
      await answerAll();
      expect(api.put.calls.allArgs().map((a) => a[0])).toEqual(['/me/email/daily_email', '/me/email/tips_email']);
    });

    it('skips a tap a later tap on the same switch has replaced', async () => {
      void service.set('daily_email', true);
      void service.set('tips_email', true);
      void service.set('tips_email', false);
      void service.set('tips_email', true);
      expect(shown()).toBe('100001');
      await answerAll();
      expect(api.put.calls.allArgs().map((a) => a[0])).toEqual(['/me/email/daily_email', '/me/email/tips_email']);
      expect(shown()).toBe('100001');
      expect(server.tips_email).toBeTrue();
    });

    it('a failed save puts back only its own switch', async () => {
      fail.add('daily_email');
      void service.set('daily_email', true);
      void service.set('weekly_email', true);
      expect(shown()).toBe('101000');
      await answerAll();
      expect(shown()).toBe('001000');
      // The later success clears the error the failure showed.
      expect(service.error()).toBeNull();
    });

    it('reports a failure that is the last word', async () => {
      fail.add('weekly_email');
      void service.set('weekly_email', true);
      await answerAll();
      expect(shown()).toBe('000000');
      expect(service.error()).toBe('That change was not saved. Try again.');
    });
  });
});
