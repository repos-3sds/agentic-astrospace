/**
 * Who a reader can call when Ask hears that they are thinking of ending their
 * life (safety.py "crisis", sweep 2026-10-29 G-1).
 *
 * Picked from the phone's time zone, not an account setting: the person may
 * be travelling, and the number has to work where they are standing now.
 * Free, confidential, round-the-clock lines run by a government or a
 * long-standing charity only, with the emergency number beside them. A
 * country not listed gets the emergency-number line and findahelpline.com,
 * which lists free lines for every country. Checked 2026-10-29; re-check
 * yearly (numbers move: India's KIRAN line folded into Tele-MANAS).
 */
export interface SupportLine {
  name: string;
  /** As printed for people. */
  display: string;
  /** Digits for tel: links. */
  dial: string;
  detail: string;
}

export interface CrisisSupport {
  country: string | null;
  lines: SupportLine[];
  /** The number for immediate danger, as people say it. */
  emergency: string;
}

const SUPPORT: Record<string, CrisisSupport> = {
  IN: {
    country: 'India',
    lines: [
      { name: 'Tele-MANAS', display: '14416', dial: '14416', detail: 'Government of India. Free, 24 hours, in your language.' },
      { name: 'Tele-MANAS (toll-free)', display: '1800 891 4416', dial: '18008914416', detail: 'The same service, from any phone.' },
    ],
    emergency: '112',
  },
  US: {
    country: 'the United States',
    lines: [{ name: '988 Suicide & Crisis Lifeline', display: '988', dial: '988', detail: 'Call or text. Free, 24 hours.' }],
    emergency: '911',
  },
  CA: {
    country: 'Canada',
    lines: [{ name: '9-8-8 Suicide Crisis Helpline', display: '988', dial: '988', detail: 'Call or text. Free, 24 hours.' }],
    emergency: '911',
  },
  GB: {
    country: 'the UK',
    lines: [{ name: 'Samaritans', display: '116 123', dial: '116123', detail: 'Free, 24 hours.' }],
    emergency: '999',
  },
  IE: {
    country: 'Ireland',
    lines: [{ name: 'Samaritans', display: '116 123', dial: '116123', detail: 'Free, 24 hours.' }],
    emergency: '112',
  },
  AU: {
    country: 'Australia',
    lines: [{ name: 'Lifeline', display: '13 11 14', dial: '131114', detail: '24 hours.' }],
    emergency: '000',
  },
  NZ: {
    country: 'New Zealand',
    lines: [{ name: 'Need to talk?', display: '1737', dial: '1737', detail: 'Call or text. Free, 24 hours.' }],
    emergency: '111',
  },
  SG: {
    country: 'Singapore',
    lines: [{ name: 'Samaritans of Singapore', display: '1767', dial: '1767', detail: '24 hours.' }],
    emergency: '995',
  },
};

const ZONES: Record<string, string> = {
  'Asia/Kolkata': 'IN', 'Asia/Calcutta': 'IN',
  'Europe/London': 'GB', 'Europe/Belfast': 'GB', 'Europe/Dublin': 'IE',
  'Asia/Singapore': 'SG', 'Pacific/Auckland': 'NZ', 'Pacific/Chatham': 'NZ',
};

const CANADA = new Set([
  'America/Toronto', 'America/Vancouver', 'America/Montreal', 'America/Edmonton', 'America/Winnipeg',
  'America/Halifax', 'America/St_Johns', 'America/Regina', 'America/Moncton', 'America/Whitehorse',
  'America/Yellowknife', 'America/Iqaluit', 'America/Glace_Bay', 'America/Goose_Bay', 'America/Dawson_Creek',
  'America/Swift_Current', 'America/Rankin_Inlet', 'America/Cambridge_Bay', 'America/Inuvik', 'America/Creston',
  'America/Fort_Nelson', 'America/Atikokan', 'America/Dawson', 'America/Resolute', 'America/Nipigon',
  'America/Thunder_Bay', 'America/Rainy_River', 'America/Pangnirtung',
]);

const US = new Set([
  'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'America/Phoenix',
  'America/Anchorage', 'America/Detroit', 'America/Boise', 'America/Juneau', 'America/Adak', 'America/Nome',
  'America/Sitka', 'America/Yakutat', 'America/Metlakatla', 'America/Menominee',
  'America/Indiana/Indianapolis', 'America/Kentucky/Louisville', 'America/North_Dakota/Center',
  'Pacific/Honolulu', 'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific', 'US/Alaska', 'US/Hawaii',
]);

export function countryForTimezone(zone: string | null | undefined): string | null {
  if (!zone) return null;
  if (ZONES[zone]) return ZONES[zone];
  if (zone.startsWith('Australia/')) return 'AU';
  if (CANADA.has(zone) || zone.startsWith('Canada/')) return 'CA';
  if (US.has(zone) || zone.startsWith('America/Indiana/') || zone.startsWith('America/Kentucky/')
    || zone.startsWith('America/North_Dakota/')) return 'US';
  return null;
}

export const FIND_A_HELPLINE = 'https://findahelpline.com';

/** The lines for the phone's time zone; an unlisted zone gets none, and the screen points to findahelpline.com. */
export function crisisSupportFor(zone: string | null | undefined): CrisisSupport {
  const code = countryForTimezone(zone);
  return (code && SUPPORT[code]) || { country: null, lines: [], emergency: 'your local emergency number' };
}
