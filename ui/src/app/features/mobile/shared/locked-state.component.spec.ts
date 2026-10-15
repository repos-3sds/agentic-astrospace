import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { EntitlementDenial } from '../../../core/entitlement-denial';
import { LockedStateComponent } from './locked-state.component';

function render(denial: EntitlementDenial): string {
  TestBed.configureTestingModule({ imports: [LockedStateComponent], providers: [provideRouter([])] });
  const fixture = TestBed.createComponent(LockedStateComponent);
  fixture.componentRef.setInput('denial', denial);
  fixture.detectChanges();
  return (fixture.nativeElement as HTMLElement).textContent ?? '';
}

describe('LockedStateComponent', () => {
  it('says when free answers come back and offers plans and packs, without fear', () => {
    const text = render({
      code: 'entitlement_limit_reached', entitlement: 'ask.answers.period', access_tier: 'free',
      remaining: 0, resets_at: '2026-11-01T00:00:00', upgrade_options: ['plus', 'pro'],
    });
    expect(text).toContain('You’ve used this month’s answers');
    expect(text).toContain('1 November');
    expect(text).toContain('Buy questions');
    expect(text).toContain('never use a question');
    expect(text.toLowerCase()).not.toMatch(/hurry|warning|danger|last chance/);
  });

  it('explains the profile limit', () => {
    const text = render({
      code: 'entitlement_limit_reached', entitlement: 'profiles.max', access_tier: 'free',
      remaining: 0, resets_at: null, upgrade_options: ['plus', 'pro'],
    });
    expect(text).toContain('Free keeps 2 profiles');
    expect(text).not.toContain('Buy questions');
  });
});
