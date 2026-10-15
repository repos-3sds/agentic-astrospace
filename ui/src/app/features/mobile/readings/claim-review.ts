import { signal } from '@angular/core';

import { PredictionClaim, PredictionClaimStatus } from '../../../core/models';
import { ReadingService } from '../../../core/reading.service';

/**
 * How a person marks a prediction, in their words rather than the ledger's.
 * The stored statuses stay `accurate | partly | missed | not_applicable`;
 * "accurate" and "missed" read as a grade, "Happened" and "Didn't happen"
 * read as what the person actually saw.
 */
export const REVIEW_OPTIONS: Array<{ status: PredictionClaimStatus; label: string; tone: 'good' | 'warn' | 'bad' | 'neutral' }> = [
  { status: 'accurate', label: 'Happened', tone: 'good' },
  { status: 'partly', label: 'Partly', tone: 'warn' },
  { status: 'missed', label: 'Didn’t happen', tone: 'bad' },
  { status: 'not_applicable', label: 'Doesn’t apply', tone: 'neutral' },
];

export function reviewLabel(status: PredictionClaimStatus): string {
  return REVIEW_OPTIONS.find((option) => option.status === status)?.label ?? 'Not checked yet';
}

const DAY = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' });

function parseDay(value: string): Date {
  const [y, m, d] = value.split('-').map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

/** "Oct 15" or "Oct 15 – Oct 21"; the claim's period label when it has no dates. */
export function claimWindow(claim: PredictionClaim): string {
  if (!claim.target_start_date) return claim.period_label ?? '';
  const start = DAY.format(parseDay(claim.target_start_date));
  if (!claim.target_end_date || claim.target_end_date === claim.target_start_date) return start;
  return `${start} – ${DAY.format(parseDay(claim.target_end_date))}`;
}

/** A prediction can be checked once its window has begun. */
export function claimIsDue(claim: PredictionClaim, today = new Date()): boolean {
  if (!claim.target_start_date) return true;
  const start = parseDay(claim.target_start_date);
  return start.getTime() <= new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
}

export const CLAIM_SAVE_ERROR = 'That didn’t save. Tap it again to retry.';

/**
 * Marking a prediction, optimistically.
 *
 * The answer shows the moment it is tapped; only that chip says it is still
 * saving, the other three stay live, and a failure puts the claim back to
 * what the server last confirmed with a one-line note on that card. Before
 * this, all four chips dimmed for the round trip and a failure swapped the
 * whole screen for the error page (production audit 2026-10-15, R7).
 *
 * `apply` writes a change into whichever lists the screen keeps.
 */
export class ClaimMarker {
  readonly saving = signal<Record<string, PredictionClaimStatus>>({});
  readonly errors = signal<Record<string, string>>({});
  private readonly seq: Record<string, number> = {};
  private readonly confirmed: Record<string, PredictionClaimStatus> = {};

  constructor(
    private readonly api: ReadingService,
    private readonly apply: (claimId: string, change: Partial<PredictionClaim>) => void,
  ) {}

  /** Tapping the chosen answer again clears it, so a mis-tap is undoable.
   * Resolves to the status saved, or null when it was not. */
  async mark(kundliId: string, claim: PredictionClaim, status: PredictionClaimStatus): Promise<PredictionClaimStatus | null> {
    const id = claim.id;
    const next: PredictionClaimStatus = claim.status === status ? 'pending' : status;
    if (!(id in this.confirmed)) this.confirmed[id] = claim.status;
    const request = (this.seq[id] = (this.seq[id] ?? 0) + 1);
    this.saving.update((map) => ({ ...map, [id]: next }));
    this.errors.update(({ [id]: _cleared, ...rest }) => rest);
    this.apply(id, { status: next });
    try {
      const updated = await this.api.claimFeedback(kundliId, id, next, claim.user_feedback ?? '');
      this.confirmed[id] = updated.status;
      if (this.seq[id] === request) this.apply(id, updated);
      return updated.status;
    } catch {
      if (this.seq[id] === request) {
        this.apply(id, { status: this.confirmed[id] });
        this.errors.update((map) => ({ ...map, [id]: CLAIM_SAVE_ERROR }));
      }
      return null;
    } finally {
      if (this.seq[id] === request) this.saving.update(({ [id]: _done, ...rest }) => rest);
    }
  }

  isSaving(claimId: string, status: PredictionClaimStatus): boolean {
    return this.saving()[claimId] === status;
  }

  reset(): void {
    this.saving.set({});
    this.errors.set({});
    for (const key of Object.keys(this.confirmed)) delete this.confirmed[key];
  }
}
