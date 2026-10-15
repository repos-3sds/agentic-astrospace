import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { NotificationsComponent } from './notifications.component';
import { PushPermission, PushService } from '../../../core/push.service';

class PushStub {
  permission = signal<PushPermission>('prompt');
  registered = signal(false);
  error = signal<string | null>(null);
  native = signal(true);
  synced: Array<[string, boolean]> = [];
  enabled = 0;
  opened = 0;
  refreshPermission = async () => this.permission();
  enable = async () => { this.enabled += 1; this.permission.set('granted'); this.registered.set(true); return this.permission(); };
  register = async () => undefined;
  openSystemSettings = async () => { this.opened += 1; };
  syncPreference = async (id: string, on: boolean) => { this.synced.push([id, on]); };
}

describe('NotificationsComponent', () => {
  let fixture: ComponentFixture<NotificationsComponent>;
  let push: PushStub;

  beforeEach(async () => {
    localStorage.clear();
    push = new PushStub();
    await TestBed.configureTestingModule({
      imports: [NotificationsComponent],
      providers: [provideRouter([]), { provide: PushService, useValue: push }],
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
    expect(text()).toContain('Delivered to this device');
    expect(button('Turn on notifications')).toBeUndefined();
  });

  it('shows the denied screen with a way to system settings and a way out', async () => {
    push.permission.set('denied');
    fixture.detectChanges();
    expect(text()).toContain('Notifications are off for Siddha');
    expect(button('Open Settings')).toBeTruthy();
    expect(button('Remind me later')).toBeTruthy();
    button('Open Settings')!.click();
    await fixture.whenStable();
    expect(push.opened).toBe(1);
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
    expect(button('Open Settings')).toBeUndefined();
  });

  it('syncs a toggle to the account as well as the device', () => {
    const remedies = (fixture.nativeElement as HTMLElement).querySelector('button[aria-label="Remedy reminders"]') as HTMLButtonElement;
    remedies.click();
    fixture.detectChanges();
    expect(push.synced).toEqual([['remedies', true]]);
    expect(JSON.parse(localStorage.getItem('astrospace.mobile.notificationPrefs')!)).toContain({ id: 'remedies', on: true });
  });
});
