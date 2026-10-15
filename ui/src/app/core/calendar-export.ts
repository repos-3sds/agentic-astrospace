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
