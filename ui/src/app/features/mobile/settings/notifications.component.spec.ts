import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { NotificationsComponent } from './notifications.component';
import { PushPermission, PushService } from '../../../core/push.service';
import { PreferencesService } from '../../../core/preferences.service';
import { EmailCategory, EmailSettingsService, EmailState } from '../../../core/email-settings.service';
import { SubhashitaService } from '../../../core/subhashita.service';

class EmailStub {
  state = signal<EmailState | null>({
    address: 'me@example.com',
    deliverable: true,
    suppressed_reason: null,
    categories: {
      daily_email: false,
      festival_email: false,
      weekly_email: false,
      monthly_email: false,
      lessons_email: false,
      tips_email: false,
    },
  });
  error = signal<string | null>(null);
  calls: Array<[EmailCategory, boolean]> = [];
  load = async () => undefined;
  set = async (id: EmailCategory, on: boolean) => {
    this.calls.push([id, on]);
    const s = this.state()!;
    this.state.set({ ...s, categories: { ...s.categories, [id]: on } });
  };
}

class PushStub {
  permission = signal<PushPermission>('prompt');
  registered = signal(false);
  error = signal<string | null>(null);
  native = signal(true);
  synced: Array<[string, boolean]> = [];
  enabled = 0;
  refreshPermission = async () => this.permission();
  enable = async () => { this.enabled += 1; this.permission.set('granted'); this.registered.set(true); return this.permission(); };
  register = async () => undefined;
  saved: Record<string, boolean> | null = null;
  loadPreferences = async () => this.saved;
  syncPreference = async (id: string, on: boolean) => { this.synced.push([id, on]); };
}

describe('NotificationsComponent', () => {
  let fixture: ComponentFixture<NotificationsComponent>;
  let push: PushStub;
  let email: EmailStub;

  beforeEach(async () => {
    localStorage.clear();
    push = new PushStub();
    email = new EmailStub();
    await TestBed.configureTestingModule({
      imports: [NotificationsComponent],
      providers: [
        provideRouter([]),
        { provide: PushService, useValue: push },
        { provide: EmailSettingsService, useValue: email },
        { provide: SubhashitaService, useValue: { sheetOn: signal(true), setSheetOn: () => undefined } },
        { provide: PreferencesService, useValue: { experienceMode: signal('balanced') } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(NotificationsComponent);
    fixture.detectChanges();
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const button = (label: string) =>
    Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'))
      .find((b) => b.textContent?.trim().startsWith(label)) as HTMLButtonElement | undefined;

  it('offers the one opt-in button before permission was asked', async () => {
    expect(button('Turn on notifications')).toBeTruthy();
    button('Turn on notifications')!.click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(push.enabled).toBe(1);
    expect(text()).toContain('Notifications are on');
    expect(text()).not.toContain('push token');
    expect(button('Turn on notifications')).toBeUndefined();
  });

  it('shows the denied screen with a one-tap way on and a way out', async () => {
    push.enable = async () => { push.enabled += 1; return push.permission(); };
    push.permission.set('denied');
    fixture.detectChanges();
    expect(text()).toContain('Notifications are off for Siddha');
    expect(button('Turn on notifications')).toBeTruthy();
    expect(button('Remind me later')).toBeTruthy();
    button('Turn on notifications')!.click();
    await fixture.whenStable();
    expect(push.enabled).toBe(1);
    button('Remind me later')!.click();
    fixture.detectChanges();
    expect(button('Remind me later')).toBeUndefined();
    expect(button('Check again')).toBeTruthy();
  });

  it('says web has no push instead of offering a button', () => {
    push.permission.set('unsupported');
    fixture.detectChanges();
    expect(text()).toContain('Not available on the web');
    expect(button('Turn on notifications')).toBeUndefined();
    expect(button('Remind me later')).toBeUndefined();
  });

  it('syncs a toggle to the account as well as the device', () => {
    const festivals = (fixture.nativeElement as HTMLElement).querySelector('button[aria-label="Festival reminders"]') as HTMLButtonElement;
    festivals.click();
    fixture.detectChanges();
    expect(push.synced).toEqual([['festivals', false]]);
    expect(JSON.parse(localStorage.getItem('astrospace.mobile.notificationPrefs')!)).toContain({ id: 'festivals', on: false });
  });

  it('shows the switches saved on the account, not the defaults', async () => {
    push.saved = { morning: false, remedies: true };
    fixture = TestBed.createComponent(NotificationsComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const checked = (label: string) =>
      (fixture.nativeElement as HTMLElement).querySelector(`button[aria-label="${label}"]`)?.getAttribute('aria-checked');
    expect(checked('Morning brief')).toBe('false');
    expect(checked('Remedy reminders')).toBe('true');
    expect(checked('Festival reminders')).toBe('true');
  });

  it('offers remedy reminders outside Practitioner too', () => {
    expect((fixture.nativeElement as HTMLElement).querySelector('button[aria-label="Remedy reminders"]')).not.toBeNull();
  });

  it('lists every email choice, all off, and saves a toggle to the account', () => {
    for (const title of ['Weekly outlook', 'Monthly outlook', 'Learn your chart', 'Tips and reminders']) {
      expect((fixture.nativeElement as HTMLElement).querySelector(`button[aria-label="${title} by email"]`))
        .withContext(title).not.toBeNull();
    }
    const daily = (fixture.nativeElement as HTMLElement).querySelector('button[aria-label="Daily reading by email"]') as HTMLButtonElement;
    expect(daily.getAttribute('aria-checked')).toBe('false');
    expect(text()).toContain('Sent to me@example.com');
    daily.click();
    fixture.detectChanges();
    expect(email.calls).toEqual([['daily_email', true]]);
    expect(daily.getAttribute('aria-checked')).toBe('true');
  });

  it('says when emails to the address bounced', () => {
    email.state.set({ ...email.state()!, deliverable: false, suppressed_reason: 'hard bounce' });
    fixture.detectChanges();
    expect(text()).toContain("couldn't be delivered");
  });
});
