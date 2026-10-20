import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { NotifyNudgeComponent } from './notify-nudge.component';
import { PushPermission, PushService } from '../../../core/push.service';
import { AuthService } from '../../../core/auth.service';

class PushStub {
  permission = signal<PushPermission>('prompt');
  native = signal(true);
  enabled = 0;
  enable = async () => { this.enabled += 1; this.permission.set('granted'); return this.permission(); };
}

describe('NotifyNudgeComponent', () => {
  let fixture: ComponentFixture<NotifyNudgeComponent>;
  let push: PushStub;

  beforeEach(async () => {
    localStorage.clear();
    push = new PushStub();
    await TestBed.configureTestingModule({
      imports: [NotifyNudgeComponent],
      providers: [
        { provide: PushService, useValue: push },
        { provide: AuthService, useValue: { isAuthenticated: () => true } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(NotifyNudgeComponent);
    fixture.detectChanges();
  });

  const el = () => fixture.nativeElement as HTMLElement;
  const button = (label: string) =>
    Array.from(el().querySelectorAll('button')).find((b) => b.textContent?.trim().startsWith(label));

  it('offers to turn notifications on and goes away once they are', async () => {
    expect(el().textContent).toContain('Get your reading each morning');
    button('Turn on notifications')!.click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(push.enabled).toBe(1);
    expect(el().querySelector('.nudge')).toBeNull();
  });

  it('still offers the way on after the system said no', () => {
    push.permission.set('denied');
    fixture.detectChanges();
    expect(button('Turn on notifications')).toBeTruthy();
  });

  it('hides on "Not now" and stays hidden on the next visit', () => {
    button('Not now')!.click();
    fixture.detectChanges();
    expect(el().querySelector('.nudge')).toBeNull();
    const again = TestBed.createComponent(NotifyNudgeComponent);
    again.detectChanges();
    expect((again.nativeElement as HTMLElement).querySelector('.nudge')).toBeNull();
  });

  it('is not shown on the web or once notifications are on', () => {
    push.native.set(false);
    fixture.detectChanges();
    expect(el().querySelector('.nudge')).toBeNull();
    push.native.set(true);
    push.permission.set('granted');
    fixture.detectChanges();
    expect(el().querySelector('.nudge')).toBeNull();
  });
});
