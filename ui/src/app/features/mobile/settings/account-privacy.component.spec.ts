import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { ApiService } from '../../../core/api.service';

import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { AccountPrivacyComponent } from './account-privacy.component';

describe('AccountPrivacyComponent › Change email', () => {
  let changeEmail: jasmine.Spy;

  beforeEach(async () => {
    changeEmail = jasmine.createSpy('changeEmail').and.resolveTo();
    await TestBed.configureTestingModule({
      imports: [AccountPrivacyComponent],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: { get: () => Promise.resolve({}) } },
        { provide: AuthService, useValue: { changeEmail, user: signal({ email: 'old@example.com' }), email: signal('old@example.com') } },
        { provide: KundliStore, useValue: { loaded: () => true, kundlis: () => [] } },
        { provide: PreferencesService, useValue: { shareUsage: signal(true), experienceMode: signal('balanced') } },
      ],
    }).compileComponents();
  });

  function open() {
    const fixture = TestBed.createComponent(AccountPrivacyComponent);
    fixture.detectChanges();
    const row = [...fixture.nativeElement.querySelectorAll('button.action')].find((b: HTMLElement) => b.textContent?.includes('Change Email')) as HTMLButtonElement;
    row.click();
    return { fixture, row };
  }

  it('opens a form under the row instead of leaving for sign-in', async () => {
    const { fixture, row } = open();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(row.getAttribute('aria-expanded')).toBe('true');
    expect(fixture.nativeElement.querySelector('#new-email')).not.toBeNull();
  });

  it('sends the confirmation link and says the change waits on it', async () => {
    const { fixture } = open();
    await fixture.whenStable();
    fixture.detectChanges();
    const input: HTMLInputElement = fixture.nativeElement.querySelector('#new-email');
    input.value = 'new@example.com';
    input.dispatchEvent(new Event('input'));
    fixture.nativeElement.querySelector('.email-form').dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    fixture.detectChanges();
    expect(changeEmail).toHaveBeenCalledOnceWith('new@example.com');
    const status = fixture.nativeElement.querySelector('[role="status"]').textContent;
    expect(status).toContain('new@example.com');
    expect(status).toContain('once you open it');
  });

  it('refuses the current address without calling Supabase', async () => {
    const { fixture } = open();
    await fixture.whenStable();
    fixture.detectChanges();
    const input: HTMLInputElement = fixture.nativeElement.querySelector('#new-email');
    input.value = 'OLD@example.com';
    input.dispatchEvent(new Event('input'));
    fixture.nativeElement.querySelector('.email-form').dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    fixture.detectChanges();
    expect(changeEmail).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('[role="alert"]').textContent).toContain('already your email');
  });
});

describe('AccountPrivacyComponent › Sign out', () => {
  it('asks once before signing out', async () => {
    const signOut = jasmine.createSpy('signOut').and.resolveTo();
    const reset = jasmine.createSpy('reset');
    await TestBed.configureTestingModule({
      imports: [AccountPrivacyComponent],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: { get: () => Promise.resolve({}) } },
        { provide: AuthService, useValue: { signOut, user: signal({ email: 'me@example.com' }), email: signal('me@example.com') } },
        { provide: KundliStore, useValue: { loaded: () => true, kundlis: () => [], reset } },
        { provide: PreferencesService, useValue: { shareUsage: signal(true), experienceMode: signal('balanced') } },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(AccountPrivacyComponent);
    fixture.detectChanges();
    const row = [...fixture.nativeElement.querySelectorAll('button.action')]
      .find((b: HTMLElement) => b.textContent?.includes('Sign Out')) as HTMLButtonElement;
    row.click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(signOut).not.toHaveBeenCalled();
    (fixture.nativeElement.querySelector('[aria-label="Confirm sign out"] .send') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(reset).toHaveBeenCalled();
    expect(signOut).toHaveBeenCalledOnceWith(['/m', 'start']);
  });
});
