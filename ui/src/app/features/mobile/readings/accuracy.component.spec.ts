import { signal } from '@angular/core';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { HapticsService } from '../../../core/haptics.service';
import { KundliStore } from '../../../core/kundli.store';
import { PredictionClaim } from '../../../core/models';
import { ReadingService } from '../../../core/reading.service';
import { AccuracyComponent, COLLAPSE_MS, SETTLE_MS } from './accuracy.component';

function claim(id: string): PredictionClaim {
  return {
    id, kundli_id: 'k1', reading_id: 'r1', reading_type: 'weekly', claim_text: `Claim ${id} will likely play out.`,
    category: 'career', status: 'pending', target_start_date: '2020-01-01', target_end_date: '2020-01-07',
  } as PredictionClaim;
}

describe('AccuracyComponent (Track record)', () => {
  let fixture: ComponentFixture<AccuracyComponent>;
  let api: jasmine.SpyObj<ReadingService>;

  const el = () => fixture.nativeElement as HTMLElement;
  const cards = () => Array.from(el().querySelectorAll<HTMLElement>('.mra-slot'));
  const chip = (card: HTMLElement, label: string) =>
    Array.from(card.querySelectorAll<HTMLButtonElement>('button')).find((b) => b.textContent?.trim() === label)!;

  function start(): void {
    fixture = TestBed.createComponent(AccuracyComponent);
    fixture.detectChanges();
    flushMicrotasks();
    fixture.detectChanges();
  }

  beforeEach(async () => {
    api = jasmine.createSpyObj<ReadingService>('ReadingService', ['claims', 'claimFeedback']);
    api.claims.and.resolveTo([claim('a'), claim('b')]);
    await TestBed.configureTestingModule({
      imports: [AccuracyComponent],
      providers: [
        provideRouter([]),
        { provide: ReadingService, useValue: api },
        { provide: HapticsService, useValue: jasmine.createSpyObj('HapticsService', ['select', 'tap']) },
        { provide: KundliStore, useValue: { activeId: signal('k1'), active: signal({ id: 'k1', name: 'Mine' }) } },
      ],
    }).compileComponents();
  });

  it('keeps a marked card under the finger, then folds it away', fakeAsync(() => {
    api.claimFeedback.and.callFake(async (_k, id, status) => ({ ...claim(id), status }));
    start();
    expect(cards().length).toBe(2);

    chip(cards()[0], 'Happened').click();
    flushMicrotasks();
    fixture.detectChanges();
    expect(cards().length).toBe(2);
    expect(chip(cards()[0], 'Happened').classList).toContain('active');
    expect(cards()[0].classList).not.toContain('collapsing');

    tick(SETTLE_MS);
    fixture.detectChanges();
    expect(cards()[0].classList).toContain('collapsing');

    tick(COLLAPSE_MS);
    fixture.detectChanges();
    expect(cards().length).toBe(1);
    expect(el().textContent).toContain('To check (1)');
  }));

  it('a failed mark stays on the card instead of replacing the screen', fakeAsync(() => {
    api.claimFeedback.and.rejectWith(new Error('offline'));
    start();

    chip(cards()[0], 'Partly').click();
    flushMicrotasks();
    fixture.detectChanges();
    tick(SETTLE_MS + COLLAPSE_MS);
    fixture.detectChanges();

    expect(cards().length).toBe(2);
    expect(chip(cards()[0], 'Partly').classList).not.toContain('active');
    expect(el().querySelector('.mra-claim-error')).not.toBeNull();
    expect(el().querySelector('as-generic-error')).toBeNull();
  }));
});
