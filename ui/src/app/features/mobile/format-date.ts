/** "Aug 2017" — the month-and-year label the chart screens share for period dates. */
export function monthYear(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * "6 Oct 1990": the month spelled out, because 6/10/1990 reads as June in
 * one country and October in another (regression 2026-10-17, R5). Built from
 * the parts, not a Date, so no timezone can move the day.
 */
export function birthDate(day: number, month: number, year: number): string {
  return `${day} ${MONTHS[month - 1] ?? month} ${year}`;
}

/** "6 Oct 2026": day, short month, year, for exact period boundaries. */
export function dayMonthYear(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
}
