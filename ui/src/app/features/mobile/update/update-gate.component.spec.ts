import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { AppUpdateService } from '../../../core/app-update.service';
import { UpdateGateComponent } from './update-gate.component';
import { UpdateSheetComponent } from './update-sheet.component';

class UpdatesStub {
  store = signal('Google Play');
  updates = 0;
  laters = 0;
  checks = 0;
  update = async () => { this.updates += 1; };
  later = () => { this.laters += 1; };
  check = async () => { this.checks += 1; };
}

describe('Update screens', () => {
  let updates: UpdatesStub;

  beforeEach(() => {
    updates = new UpdatesStub();
    TestBed.configureTestingModule({ providers: [{ provide: AppUpdateService, useValue: updates }] });
  });

  const button = (el: HTMLElement, label: string) =>
    Array.from(el.querySelectorAll('button')).find((b) => b.textContent?.trim() === label)!;

  it('the block says what to do and where, and checks again on request', () => {
    const fixture = TestBed.createComponent(UpdateGateComponent);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Please update Siddha');
    expect(el.textContent).toContain('Google Play');
    expect(el.querySelector('[role="alertdialog"]')).toBeTruthy();
    button(el, 'Update now').click();
    button(el, 'I have updated').click();
    expect(updates.updates).toBe(1);
    expect(updates.checks).toBe(1);
  });

  it('the sheet can be put off, and never says what is new', () => {
    const fixture = TestBed.createComponent(UpdateSheetComponent);
    fixture.detectChanges();
    const el = document.body;
    expect(el.textContent).toContain('A new version of Siddha is ready');
    button(el, 'Later').click();
    expect(updates.laters).toBeGreaterThanOrEqual(1);
    fixture.destroy();
  });
});
