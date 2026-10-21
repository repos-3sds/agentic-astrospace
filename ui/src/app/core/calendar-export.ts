import { Capacitor, registerPlugin } from '@capacitor/core';
import { IcsEvent, buildIcs, googleCalendarUrl } from './ics';
import { shareFile } from './native-share';

/**
 * Hands an .ics file to the phone: the share sheet on a device (where
 * Calendar is one of the targets), a plain download in a browser. Throws
 * only when neither is possible, so the caller can say so inline.
 */
export async function exportCalendarFile(ics: string, fileName: string, title: string): Promise<void> {
  const file = new File([ics], fileName, { type: 'text/calendar' });
  if (await shareFile(file, { title })) return;
  const url = URL.createObjectURL(file);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

interface NativeCalendarPlugin {
  insert(options: {
    title: string;
    begin: number;
    end: number;
    allDay: boolean;
    description?: string;
    location?: string;
  }): Promise<void>;
}

const NativeCalendar = registerPlugin<NativeCalendarPlugin>('NativeCalendar');

/**
 * Epoch milliseconds for the native calendar form. All-day events are UTC
 * midnights with an exclusive end, the way Android's CalendarContract
 * stores them; `endIso` is the last day covered.
 */
export function nativeEventTimes(event: IcsEvent): { begin: number; end: number } {
  if (event.allDay) {
    const day = (iso: string) => {
      const [y, m, d] = iso.split('-').map(Number);
      return Date.UTC(y, m - 1, d);
    };
    return { begin: day(event.startIso), end: day(event.endIso) + 86_400_000 };
  }
  return { begin: new Date(event.startIso).getTime(), end: new Date(event.endIso).getTime() };
}

/**
 * Puts one event in the phone's calendar. On Android that is the phone's
 * calendar app's add-event form (an .ics file there only reaches the share
 * sheet, retest of build 487); everywhere else the .ics file, which iOS
 * Calendar and desktop calendars open directly.
 */
export async function addToCalendar(event: IcsEvent, fileName: string): Promise<void> {
  if (Capacitor.getPlatform() === 'android') {
    // The phone's own calendar app (Samsung Calendar as well as Google's)
    // on a filled-in new-event form (audit N18). A build without the
    // plugin, or a phone with no calendar app, falls back to the Google
    // Calendar link, which the system opens in the app or the browser.
    try {
      await NativeCalendar.insert({
        title: event.title,
        ...nativeEventTimes(event),
        allDay: !!event.allDay,
        description: event.description,
        location: event.location,
      });
      return;
    } catch {
      window.location.href = googleCalendarUrl(event);
      return;
    }
  }
  await exportCalendarFile(buildIcs([event]), fileName, event.title);
}
