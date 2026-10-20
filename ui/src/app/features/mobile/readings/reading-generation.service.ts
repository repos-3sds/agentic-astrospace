import { Injectable, inject, signal } from '@angular/core';

import { EntitlementDenial, EntitlementLimitError } from '../../../core/entitlement-denial';
import { Reading } from '../../../core/models';
import { ReadingPeriod, ReadingService } from '../../../core/reading.service';

export interface GenerationJob {
  kundliId: string;
  period: ReadingPeriod;
  /** True for "New version", false for the first reading of a period. */
  force: boolean;
  startedAt: number;
  status: 'running' | 'done' | 'error';
  reading?: Reading;
  error?: string;
  /** HTTP status of a failed run; 429 is the daily new-version allowance. */
  errorStatus?: number;
  /** Set when the month's readings are used up (402). */
  denial?: EntitlementDenial;
}

export function generationKey(kundliId: string, period: ReadingPeriod): string {
  return `${kundliId}:${period}`;
}

/**
 * Reading generations in flight, held above the Readings screen.
 *
 * A reading takes 20–40 s. The screen is not a retained tab, so its own
 * state died when the person stepped away (to Ask, or back to the chart)
 * and the reading they were waiting for arrived to nobody: no progress on
 * return, and a second tap started a second paid generation (production
 * audit 2026-10-15, R6). The job lives here instead; the screen reads it on
 * return, shows progress for a running one and picks up a finished one.
 */
@Injectable({ providedIn: 'root' })
export class ReadingGenerationService {
  private readonly api = inject(ReadingService);
  private readonly jobsState = signal<Record<string, GenerationJob>>({});
  readonly jobs = this.jobsState.asReadonly();

  job(kundliId: string, period: ReadingPeriod): GenerationJob | null {
    return this.jobsState()[generationKey(kundliId, period)] ?? null;
  }

  /** Start one, unless one is already running for this profile and period. */
  start(kundliId: string, period: ReadingPeriod, force: boolean): void {
    const key = generationKey(kundliId, period);
    if (this.jobsState()[key]?.status === 'running') return;
    this.put(key, { kundliId, period, force, startedAt: Date.now(), status: 'running' });
    this.api.generate(kundliId, period, force).then(
      (reading) => this.patch(key, { status: 'done', reading }),
      (error: unknown) => this.patch(key, {
        status: 'error',
        error: (error as Error)?.message ?? String(error),
        errorStatus: (error as { status?: number })?.status,
        denial: error instanceof EntitlementLimitError ? error.denial : undefined,
      }),
    );
  }

  /** The screen has shown a finished job's outcome. */
  clear(kundliId: string, period: ReadingPeriod): void {
    const key = generationKey(kundliId, period);
    const current = this.jobsState()[key];
    if (!current || current.status === 'running') return;
    this.jobsState.update(({ [key]: _gone, ...rest }) => rest);
  }

  private put(key: string, job: GenerationJob): void {
    this.jobsState.update((jobs) => ({ ...jobs, [key]: job }));
  }

  private patch(key: string, change: Partial<GenerationJob>): void {
    this.jobsState.update((jobs) => (jobs[key] ? { ...jobs, [key]: { ...jobs[key], ...change } } : jobs));
  }
}
