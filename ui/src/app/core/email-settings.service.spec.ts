import { TestBed } from '@angular/core/testing';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import {
  EmailSettingsService,
  clearEmailOptIn,
  rememberEmailOptIn,
  storedEmailOptIn,
} from './email-settings.service';

describe('EmailSettingsService', () => {
  let service: EmailSettingsService;
  let api: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    clearEmailOptIn();
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

  afterEach(() => clearEmailOptIn());

  it('carries the sign-up box across onboarding', () => {
    expect(storedEmailOptIn()).toBeNull();
    rememberEmailOptIn(true);
    expect(storedEmailOptIn()).toBe('yes');
    rememberEmailOptIn(false);
    expect(storedEmailOptIn()).toBe('no');
    clearEmailOptIn();
    expect(storedEmailOptIn()).toBeNull();
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
});
