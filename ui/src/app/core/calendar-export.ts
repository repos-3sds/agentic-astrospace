import { Capacitor } from '@capacitor/core';
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

/**
 * Puts one event in the phone's calendar. On Android that is Google
 * Calendar's add-event form (an .ics file there only reaches the share
 * sheet, retest of build 487); everywhere else the .ics file, which iOS
 * Calendar and desktop calendars open directly.
 */
export async function addToCalendar(event: IcsEvent, fileName: string): Promise<void> {
  if (Capacitor.getPlatform() === 'android') {
    // The native bridge hands an off-app navigation to the system, which
    // opens the Calendar app when it claims the link, else the browser.
    window.location.href = googleCalendarUrl(event);
    return;
  }
  await exportCalendarFile(buildIcs([event]), fileName, event.title);
}
