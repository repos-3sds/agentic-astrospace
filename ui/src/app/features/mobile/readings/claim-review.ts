import { PredictionClaim, PredictionClaimStatus } from '../../../core/models';

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
