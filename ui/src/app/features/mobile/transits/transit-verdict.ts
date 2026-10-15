/**
 * One vocabulary for a transit's verdict on every screen. Gochara printed the
 * engine's words ("mixed", "challenging") while Full Transits folded
 * everything that wasn't supportive into "needs care", so the same placement
 * read differently on the two tabs.
 */
const LABELS: Record<string, string> = {
  supportive: 'supportive',
  mixed: 'mixed',
  challenging: 'needs care',
  neutral: 'steady',
};

export function transitVerdictLabel(verdict: string | null | undefined): string {
  return verdict ? LABELS[verdict] ?? verdict : 'steady';
}
