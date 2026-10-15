import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { HapticsService } from '../../../core/haptics.service';
import { KundliStore } from '../../../core/kundli.store';
import { PredictionClaim, Reading } from '../../../core/models';
import { ReadingService } from '../../../core/reading.service';
import { ReadingGenerationService } from './reading-generation.service';
import { ReadingsComponent, periodTitle, splitReadings } from './readings.component';

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function reading(id: string, over: Partial<Reading> = {}): Reading {
  return {
    id,
    kundli_id: 'k1',
    reading_type: 'weekly',
    period_label: 'Week of Oct 12, 2026',
    period_start: '2026-10-12',
    period_end: '2026-10-18',
    is_current_period: true,
    version: 1,
    content: `## Overall theme\nReading ${id}.`,
    generated_at: '2026-10-13T08:00:00Z',
    generated_local_date: '2026-10-13',
    ...over,
  };
}

const WEEK_V2 = reading('v2', { version: 2, generated_at: '2026-10-15T08:00:00Z', generated_local_date: '2026-10-15' });
const WEEK_V1 = reading('v1');
const LAST_WEEK = reading('past', {
  period_label: 'Week of Oct 5, 2026', period_start: '2026-10-05', period_end: '2026-10-11',
  is_current_period: false, generated_at: '2026-10-06T08:00:00Z', generated_local_date: '2026-10-06',
});
const TWO_WEEKS_AGO = reading('older', {
  period_label: 'Week of Sep 28, 2026', period_start: '2026-09-28', period_end: '2026-10-04',
  is_current_period: false, generated_at: '2026-09-29T08:00:00Z', generated_local_date: '2026-09-29',
});

function claim(id: string, readingId: string): PredictionClaim {
  return {
    id, kundli_id: 'k1', reading_id: readingId, reading_type: 'weekly', claim_text: `Claim ${id} will likely play out.`,
    category: 'career', status: 'pending', target_start_date: '2026-10-12', target_end_date: '2026-10-18',
  } as PredictionClaim;
}

describe('splitReadings', () => {
  it('keeps versions of this period apart from past periods', () => {
    const { current, past } = splitReadings([LAST_WEEK, WEEK_V1, TWO_WEEKS_AGO, WEEK_V2]);
    expect(current.map((r) => r.id)).toEqual(['v2', 'v1']);
    expect(past.map((r) => r.id)).toEqual(['past', 'older']);
  });

  it('falls back to the newest label when the server does not flag rows', () => {
    const unflagged = [WEEK_V2, WEEK_V1, LAST_WEEK].map((r) => ({ ...r, is_current_period: undefined }));
    const { current, past } = splitReadings(unflagged);
    expect(current.map((r) => r.id)).toEqual(['v2', 'v1']);
    expect(past.map((r) => r.id)).toEqual(['past']);
  });

  it('titles a reading by the dates it covers', () => {
    expect(periodTitle(LAST_WEEK)).toMatch(/Oct\s*5\s*[–-]\s*11/);
    expect(periodTitle(TWO_WEEKS_AGO)).toMatch(/Sep\s*28\s*[–-]\s*Oct\s*4/);
    expect(periodTitle(reading('m', { reading_type: 'monthly', period_start: '2026-09-01', period_end: '2026-09-30' })))
      .toContain('September');
  });
});

describe('ReadingsComponent', () => {
  let fixture: ComponentFixture<ReadingsComponent>;
  let api: jasmine.SpyObj<ReadingService>;
  let haptics: jasmine.SpyObj<HapticsService>;
  let scroll: jasmine.Spy;

  async function create(): Promise<void> {
    fixture = TestBed.createComponent(ReadingsComponent);
    fixture.detectChanges();
    await settle();
  }

  // Not whenStable(): the elapsed counter's interval keeps the zone busy for
  // as long as a generation runs. A few macrotask turns let promises settle.
  async function settle(): Promise<void> {
    for (let i = 0; i < 5; i++) {
      await new Promise((resolve) => setTimeout(resolve));
      fixture.detectChanges();
    }
  }

  const el = () => fixture.nativeElement as HTMLElement;
  const text = () => el().textContent ?? '';
  const rows = () => Array.from(el().querySelectorAll<HTMLButtonElement>('button.mrd-earlier'));
  const button = (label: string) =>
    Array.from(el().querySelectorAll<HTMLButtonElement>('button')).find((b) => b.textContent?.trim() === label);

  beforeEach(async () => {
    api = jasmine.createSpyObj<ReadingService>('ReadingService', ['list', 'claims', 'generate', 'claimFeedback']);
    api.list.and.resolveTo([WEEK_V2, WEEK_V1, LAST_WEEK, TWO_WEEKS_AGO]);
    api.claims.and.resolveTo([claim('c1', 'v2'), claim('c2', 'v1')]);
    haptics = jasmine.createSpyObj<HapticsService>('HapticsService', ['tap', 'press', 'select', 'success', 'warning', 'error']);
    scroll = spyOn(Element.prototype, 'scrollIntoView');

    await TestBed.configureTestingModule({
      imports: [ReadingsComponent],
      providers: [
        provideRouter([]),
        { provide: ReadingService, useValue: api },
        { provide: HapticsService, useValue: haptics },
        { provide: KundliStore, useValue: { activeId: signal('k1'), active: signal({ id: 'k1', name: 'Mine' }) } },
      ],
    }).compileComponents();
  });

  it('lists versions of this week and past weeks by date, never all "Version 1"', async () => {
    await create();
    expect(text()).toContain('VERSIONS OF THIS WEEK');
    expect(text()).toContain('PAST WEEKS');
    const titles = rows().map((row) => row.querySelector('b')?.textContent?.trim());
    expect(titles[0]).toBe('Version 2 (latest)');
    expect(titles[1]).toBe('Version 1');
    expect(titles[2]).toMatch(/Oct\s*5\s*[–-]\s*11/);
    expect(titles[3]).toMatch(/Sep\s*28/);
    expect(el().querySelector('.mrd-reading em')?.textContent).toContain('Latest');
  });

  it('tapping an earlier version keeps the list in place, marks it, and scrolls the article into view', async () => {
    await create();
    const titles = () => rows().map((row) => row.querySelector('b')?.textContent);
    const before = titles();
    rows()[1].click();
    await settle();

    expect(rows().length).toBe(4);
    expect(rows()[1].classList).toContain('on');
    expect(rows()[1].getAttribute('aria-current')).toBe('true');
    expect(rows()[1].textContent).toContain('Viewing');
    expect(titles()).toEqual(before);
    expect(rows()[0].textContent).not.toContain('Viewing');
    expect(el().querySelector('.mrd-reading .mrd-prose')?.textContent).toContain('Reading v1');
    expect(el().querySelector('.mrd-reading .mrd-older')).not.toBeNull();
    expect(haptics.select).toHaveBeenCalled();
    expect(scroll).toHaveBeenCalledWith(jasmine.objectContaining({ block: 'start' }));
  });

  it('asks before writing a new version, keeps the reading on screen, and survives leaving', async () => {
    const pending = deferred<Reading>();
    api.generate.and.returnValue(pending.promise);
    await create();

    button('New version')!.click();
    await settle();
    expect(api.generate).not.toHaveBeenCalled();
    expect(text()).toContain('Write a new version?');

    button('Write new version')!.click();
    await settle();
    expect(api.generate).toHaveBeenCalledOnceWith('k1', 'weekly', true);
    expect(el().querySelector('.mrd-progress')).not.toBeNull();
    expect(el().querySelector('.mrd-reading .mrd-prose')?.textContent).toContain('Reading v2');

    // Leave and come back while it is still writing.
    fixture.destroy();
    await create();
    expect(el().querySelector('.mrd-progress')).not.toBeNull();
    expect(api.generate).toHaveBeenCalledTimes(1);

    const v3 = reading('v3', { version: 3, generated_at: '2026-10-15T09:00:00Z', content: 'Reading v3.' });
    pending.resolve(v3);
    await settle();
    expect(el().querySelector('.mrd-progress')).toBeNull();
    expect(el().querySelector('.mrd-reading .mrd-prose')?.textContent).toContain('Reading v3');
    expect(TestBed.inject(ReadingGenerationService).jobs()).toEqual({});
  });

  it('the daily new-version allowance reads as a limit, not a failure to retry', async () => {
    api.generate.and.callFake(() => Promise.reject(Object.assign(
      new Error('You’ve asked for 3 new versions of this weekly reading today. You can ask for another tomorrow.'),
      { status: 429 },
    )));
    await create();
    button('New version')!.click();
    await settle();
    button('Write new version')!.click();
    await settle();
    expect(text()).toContain('No more new versions today');
    expect(text()).toContain('tomorrow');
    expect(button('Try again')).toBeUndefined();
    expect(el().querySelector('.mrd-reading .mrd-prose')?.textContent).toContain('Reading v2');
  });

  it('a first reading of the period does not force a regeneration', async () => {
    api.list.and.resolveTo([LAST_WEEK]);
    api.generate.and.resolveTo(reading('new'));
    await create();
    expect(text()).toContain('No weekly reading for this week yet');
    button('Get my weekly reading')!.click();
    await settle();
    expect(api.generate).toHaveBeenCalledOnceWith('k1', 'weekly', false);
  });

  it('marks a prediction at once and reverts it inline when saving fails', async () => {
    const save = deferred<PredictionClaim>();
    api.claimFeedback.and.returnValue(save.promise);
    await create();

    button('Happened')!.click();
    fixture.detectChanges();
    const happened = button('Happened')!;
    expect(happened.classList).toContain('on');
    expect(happened.classList).toContain('saving');
    expect(button('Partly')!.disabled).toBeFalse();

    save.reject(new Error('offline'));
    await settle();
    expect(button('Happened')!.classList).not.toContain('on');
    expect(el().querySelector('.mrd-claim-error')?.textContent).toContain('didn’t save');
    expect(el().querySelector('as-generic-error')).toBeNull();
  });
});
