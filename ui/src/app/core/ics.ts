/**
 * A minimal RFC 5545 calendar file for one or more timed events.
 *
 * Times are written in UTC (`…Z`) from offset-aware ISO strings, so the
 * calendar app shows each window in whatever zone the phone is in without
 * this file carrying VTIMEZONE blocks. A `VALARM` makes the calendar app
 * the reminder: Muhurta has no notification of its own to schedule, and a
 * calendar alert survives the app being closed or uninstalled.
 */
export interface IcsEvent {
  uid: string;
  title: string;
  /** An offset-aware instant, or `YYYY-MM-DD` when `allDay` is set. */
  startIso: string;
  /** For an all-day event, the last day it covers (inclusive). */
  endIso: string;
  /** A date, not a time: festivals fall on a day wherever the phone is. */
  allDay?: boolean;
  description?: string;
  location?: string;
  /** Minutes before the start to alert; omitted for no alert. */
  alarmMinutes?: number;
  /** For an all-day event: minutes after the day begins to alert (420 = 7 am). */
  alarmAfterStartMinutes?: number;
}

export function buildIcs(events: IcsEvent[], now = new Date()): string {
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//AstroSpace//Muhurta//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH'];
  for (const event of events) {
    lines.push(
      'BEGIN:VEVENT',
      `UID:${event.uid}`,
      `DTSTAMP:${utcStamp(now)}`,
      ...(event.allDay
        ? [`DTSTART;VALUE=DATE:${dateStamp(event.startIso)}`, `DTEND;VALUE=DATE:${dateStamp(event.endIso, 1)}`]
        : [`DTSTART:${utcStamp(new Date(event.startIso))}`, `DTEND:${utcStamp(new Date(event.endIso))}`]),
      `SUMMARY:${escapeText(event.title)}`,
    );
    if (event.description) lines.push(`DESCRIPTION:${escapeText(event.description)}`);
    if (event.location) lines.push(`LOCATION:${escapeText(event.location)}`);
    const trigger = event.allDay && event.alarmAfterStartMinutes != null
      ? `TRIGGER:PT${event.alarmAfterStartMinutes}M`
      : event.alarmMinutes != null ? `TRIGGER:-PT${event.alarmMinutes}M` : null;
    if (trigger) {
      lines.push('BEGIN:VALARM', 'ACTION:DISPLAY', `DESCRIPTION:${escapeText(event.title)}`, trigger, 'END:VALARM');
    }
    lines.push('END:VEVENT');
  }
  lines.push('END:VCALENDAR');
  return lines.map(fold).join('\r\n') + '\r\n';
}

function utcStamp(date: Date): string {
  if (Number.isNaN(date.getTime())) throw new Error('Invalid event time');
  return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
}

/** `YYYY-MM-DD` (plus `addDays`) as an iCalendar DATE; no time zone is involved. */
function dateStamp(isoDate: string, addDays = 0): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);
  if (!match) throw new Error('Invalid event date');
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]) + addDays));
  return date.toISOString().slice(0, 10).replace(/-/g, '');
}

function escapeText(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/([,;])/g, '\\$1');
}

/** Lines longer than 75 octets continue on the next line after a space. */
function fold(line: string): string {
  const bytes = new TextEncoder().encode(line);
  if (bytes.length <= 75) return line;
  const parts: string[] = [];
  let current = '';
  let size = 0;
  for (const char of line) {
    const width = new TextEncoder().encode(char).length;
    if (size + width > (parts.length ? 74 : 75)) {
      parts.push(current);
      current = '';
      size = 0;
    }
    current += char;
    size += width;
  }
  parts.push(current);
  return parts.join('\r\n ');
}
