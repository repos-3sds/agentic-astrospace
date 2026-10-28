import { Injectable, effect, inject, signal, untracked } from '@angular/core';
import { Router } from '@angular/router';
import { Capacitor } from '@capacitor/core';
import type { LocalNotificationSchema } from '@capacitor/local-notifications';

import { AuthService } from './auth.service';
import { KundliStore } from './kundli.store';
import { PanchangaWindow, TimingsPayload } from './models';
import { PanchangaService } from './panchanga.service';
import { PreferencesService } from './preferences.service';
import { PushService } from './push.service';
import { SessionTeardown } from './session-teardown';

/** How an alarm sounds. */
export type AlarmStyle = 'alarm' | 'bell' | 'silent';

/** Minutes before the timing starts; 0 is "when it starts". */
export type AlarmLead = 0 | 5 | 10 | 15 | 30;

export interface PanchangAlarm {
  id: string;
  /** The window name as the panchanga payload spells it; null for sunrise/sunset. */
  window: string | null;
  title: string;
  detail: string;
  /** One plain line for the notification itself. */
  note: string;
  group: 'good' | 'careful';
  on: boolean;
  lead: AlarmLead;
  style: AlarmStyle;
  /** Also a short note when the timing is over. */
  atEnd: boolean;
}

/** The exact-alarm grant Android 12+ asks for separately from notifications. */
export type ExactState = 'granted' | 'denied' | 'unsupported';

export const ALARM_STORAGE_KEY = 'astrospace.mobile.panchangAlarms';
const SCHEDULED_KEY = 'astrospace.mobile.panchangAlarms.scheduledAt';
const HANDOFF_KEY = 'astrospace.mobile.panchangAlarms.serverOff';

/** Android channels, created in MainActivity. */
const CHANNEL: Record<AlarmStyle, string> = {
  alarm: 'siddha_alarm',
  bell: 'siddha_windows',
  silent: 'siddha_quiet',
};

/** Days scheduled ahead, and the day the "open Siddha" note lands on. */
export const DAYS_AHEAD = 14;
const KEEP_GOING_DAY = 12;
/** Android lets an app hold 500 alarms; leave room for everything else. */
const MAX_SCHEDULED = 400;
/** Our notification ids live in their own range so a cancel never touches another feature's. */
const ID_BASE = 1_700_000_000;
const ID_SPAN = 100_000_000;
/** Opening the app more often than this does not re-fetch a fortnight of timings. */
const REFRESH_AFTER_MS = 6 * 60 * 60 * 1000;

export const DEFAULT_ALARMS: readonly PanchangAlarm[] = [
  { id: 'brahma', window: 'Brahma Muhurta', title: 'Brahma Muhurta', detail: 'Before sunrise, for prayer and study', note: 'A quiet time for prayer and study.', group: 'good', on: false, lead: 0, style: 'alarm', atEnd: false },
  { id: 'sunrise', window: null, title: 'Sunrise', detail: 'Morning sandhya and Surya namaskar', note: 'Time for morning sandhya.', group: 'good', on: false, lead: 0, style: 'bell', atEnd: false },
  { id: 'abhijit', window: 'Abhijit Muhurta', title: 'Abhijit Muhurta', detail: 'Midday, good for important starts', note: 'A good window for important starts.', group: 'good', on: true, lead: 0, style: 'bell', atEnd: false },
  { id: 'amrit', window: 'Amrit Kalam', title: 'Amrit Kalam', detail: 'A good window, moves every day', note: 'A good window for prayer and good work.', group: 'good', on: false, lead: 0, style: 'bell', atEnd: false },
  { id: 'godhuli', window: 'Godhuli', title: 'Godhuli', detail: 'Dusk, for lighting the lamp', note: 'A good time to light the lamp.', group: 'good', on: false, lead: 0, style: 'bell', atEnd: false },
  { id: 'sunset', window: null, title: 'Sunset', detail: 'Evening sandhya', note: 'Time for evening sandhya.', group: 'good', on: false, lead: 0, style: 'bell', atEnd: false },
  { id: 'rahu', window: 'Rahu Kalam', title: 'Rahu Kalam', detail: 'Pause new beginnings till it ends', note: 'Good to hold new beginnings till it ends.', group: 'careful', on: true, lead: 10, style: 'bell', atEnd: false },
  { id: 'yama', window: 'Yamaganda', title: 'Yamaganda', detail: 'Pause new starts and travel', note: 'Good to hold new starts and travel till it ends.', group: 'careful', on: false, lead: 10, style: 'bell', atEnd: false },
  { id: 'gulika', window: 'Gulika Kalam', title: 'Gulika Kalam', detail: 'Pause new starts', note: 'Good to hold new starts till it ends.', group: 'careful', on: false, lead: 10, style: 'bell', atEnd: false },
  { id: 'durmuhurta', window: 'Durmuhurta', title: 'Durmuhurta', detail: 'Short times to keep clear of ceremonies', note: 'Keep ceremonies clear of this short time.', group: 'careful', on: false, lead: 10, style: 'silent', atEnd: false },
  { id: 'varjya', window: 'Varjya', title: 'Varjyam', detail: 'A careful window, moves every day', note: 'Good to hold new starts till it ends.', group: 'careful', on: false, lead: 10, style: 'silent', atEnd: false },
  { id: 'bhadra', window: 'Bhadra', title: 'Bhadra', detail: 'Keep clear of auspicious starts', note: 'Keep auspicious starts clear of this time.', group: 'careful', on: false, lead: 10, style: 'silent', atEnd: false },
];

/** One occurrence of a timing on one day. */
interface Occurrence {
  start: Date;
  end: Date | null;
  /** "4:01 pm" in the timing place's clock, as the payload printed it. */
  startText: string;
  endText: string | null;
}

/**
 * Panchang alarms, scheduled on the phone.
 *
 * The server's window alerts arrive on the worker's 15-minute beat and need a
 * network; an alarm for Brahma Muhurta has to ring at 4:15 with the phone in
 * airplane mode. So the app asks the server once for a fortnight of timings
 * (GET /panchanga/{id}/timings, the same place and clock as Today) and hands
 * each one to Android's alarm manager through local notifications. The plugin
 * re-arms them after a reboot.
 *
 * Re-scheduled when a choice changes, when the timing place changes, and when
 * the app opens (at most every six hours). The last scheduled day carries a
 * quiet note asking the reader to open Siddha, since nothing can top the list
 * up without the app.
 *
 * Exact timing on Android 12+ needs the "Alarms and reminders" grant. The
 * plugin opens that settings page on every schedule() it is missing for, so
 * background refreshes ask for inexact alarms unless it is already granted;
 * only turning an alarm on from the screen asks (requestExact).
 *
 * Once this phone schedules its own, the account's server window alerts are
 * turned off, so nobody hears the same Rahu Kalam twice.
 */
@Injectable({ providedIn: 'root' })
export class PanchangAlarmService {
  private readonly panchanga = inject(PanchangaService);
  private readonly kundlis = inject(KundliStore);
  private readonly preferences = inject(PreferencesService);
  private readonly push = inject(PushService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly native = Capacitor.isNativePlatform();
  readonly alarms = signal<PanchangAlarm[]>(restoreAlarms());
  readonly exact = signal<ExactState>(Capacitor.getPlatform() === 'android' ? 'denied' : 'unsupported');
  /** Why the last schedule failed, for the screen; null while fine. */
  readonly error = signal<string | null>(null);

  private started = false;
  private running: Promise<void> | null = null;
  private again = false;

  constructor() {
    inject(SessionTeardown).register(() => void this.cancelAll());
    // A new timing place moves every alarm.
    effect(() => {
      this.preferences.panchangaPlace();
      if (this.started) untracked(() => void this.reschedule(true));
    });
  }

  /** Called once the app knows who is signed in (AppBoot). */
  async init(): Promise<void> {
    if (!this.native || this.started) return;
    this.started = true;
    try {
      const { LocalNotifications } = await import('@capacitor/local-notifications');
      await LocalNotifications.addListener('localNotificationActionPerformed', ({ notification }) => {
        if (notification.extra?.kind === 'panchang') void this.router.navigateByUrl('/m/today');
      });
      const { App } = await import('@capacitor/app');
      await App.addListener('appStateChange', ({ isActive }) => {
        if (isActive) void this.reschedule();
      });
    } catch {
      // Without the plugin there is nothing to schedule; the screen still saves choices.
    }
    await this.reschedule();
  }

  update(id: string, patch: Partial<PanchangAlarm>): void {
    this.alarms.update((all) => all.map((a) => (a.id === id ? { ...a, ...patch } : a)));
    persistAlarms(this.alarms());
    void this.reschedule(true);
  }

  async refreshExact(): Promise<void> {
    if (Capacitor.getPlatform() !== 'android') return;
    try {
      const { LocalNotifications } = await import('@capacitor/local-notifications');
      const { exact_alarm } = await LocalNotifications.checkExactNotificationSetting();
      this.exact.set(exact_alarm === 'granted' ? 'granted' : 'denied');
    } catch {
      this.exact.set('unsupported');
    }
  }

  /** Opens Android's "Alarms and reminders" page for Siddha. */
  async requestExact(): Promise<void> {
    if (Capacitor.getPlatform() !== 'android') return;
    try {
      const { LocalNotifications } = await import('@capacitor/local-notifications');
      const { exact_alarm } = await LocalNotifications.changeExactNotificationSetting();
      this.exact.set(exact_alarm === 'granted' ? 'granted' : 'denied');
    } catch {
      // The settings page could not open; alarms stay inexact.
    }
    void this.reschedule(true);
  }

  /** Coalesces overlapping calls: one run at a time, one more after if asked. */
  reschedule(force = false): Promise<void> {
    if (!this.native || !this.started) return Promise.resolve();
    if (this.running) {
      if (force) this.again = true;
      return this.running;
    }
    this.running = this.run(force).finally(() => {
      this.running = null;
      if (this.again) {
        this.again = false;
        void this.reschedule(true);
      }
    });
    return this.running;
  }

  private async run(force: boolean): Promise<void> {
    if (!force && Date.now() - lastScheduled() < REFRESH_AFTER_MS) return;
    if (!this.auth.isAuthenticated()) return;
    const { LocalNotifications } = await import('@capacitor/local-notifications');
    await this.refreshExact();
    const wanted = this.alarms().filter((a) => a.on);
    if (!wanted.length) {
      await this.cancelAll();
      return;
    }
    try {
      if (!this.kundlis.loaded()) await this.kundlis.load();
      const kundli = this.kundlis.owner() ?? this.kundlis.active();
      if (!kundli) return;
      const timings = await this.panchanga.timings(kundli.id, DAYS_AHEAD);
      const notifications = buildNotifications(timings, wanted, new Date(), this.exact() === 'granted');
      await this.cancelAll();
      if (notifications.length) await LocalNotifications.schedule({ notifications });
      try { localStorage.setItem(SCHEDULED_KEY, String(Date.now())); } catch { /* storage unavailable */ }
      this.error.set(null);
      await this.handOffFromServer();
    } catch {
      // Keep what is already scheduled; the next open tries again.
      this.error.set('Could not update your alarms. They will update the next time you open Siddha.');
    }
  }

  /** Window alerts used to come from the server; this phone has them now. */
  private async handOffFromServer(): Promise<void> {
    try {
      if (localStorage.getItem(HANDOFF_KEY)) return;
    } catch {
      return;
    }
    await this.push.syncPreference('windows', false);
    try { localStorage.setItem(HANDOFF_KEY, '1'); } catch { /* storage unavailable */ }
  }

  private async cancelAll(): Promise<void> {
    if (!this.native) return;
    try {
      const { LocalNotifications } = await import('@capacitor/local-notifications');
      const { notifications } = await LocalNotifications.getPending();
      const ours = notifications.filter((n) => isOurs(n.id));
      if (ours.length) await LocalNotifications.cancel({ notifications: ours.map((n) => ({ id: n.id })) });
      localStorage.removeItem(SCHEDULED_KEY);
    } catch {
      // Nothing pending, or the plugin is missing.
    }
  }
}

/**
 * Every notification for the fortnight, in time order, capped. Pure, so the
 * spec can check the copy and the arithmetic without a phone.
 */
export function buildNotifications(
  timings: TimingsPayload,
  alarms: readonly PanchangAlarm[],
  now: Date,
  exact: boolean,
): LocalNotificationSchema[] {
  const out: LocalNotificationSchema[] = [];
  const seen = new Set<string>();
  for (const day of timings.days) {
    for (const alarm of alarms) {
      for (const occurrence of occurrencesFor(day, alarm)) {
        const key = `${alarm.id}:${occurrence.start.toISOString()}`;
        // Varjya and night windows can sit in two days' lists.
        if (seen.has(key)) continue;
        seen.add(key);
        const at = new Date(occurrence.start.getTime() - alarm.lead * 60_000);
        if (at > now) out.push(startNotification(alarm, occurrence, at, exact));
        if (alarm.atEnd && occurrence.end && occurrence.end > now) {
          out.push(endNotification(alarm, occurrence, exact));
        }
      }
    }
  }
  out.sort((a, b) => a.schedule!.at!.getTime() - b.schedule!.at!.getTime());
  const capped = out.slice(0, MAX_SCHEDULED - 1);
  const keepGoing = keepGoingNote(timings, now);
  if (keepGoing) capped.push(keepGoing);
  return capped;
}

function occurrencesFor(day: TimingsPayload['days'][number], alarm: PanchangAlarm): Occurrence[] {
  if (alarm.id === 'sunrise' || alarm.id === 'sunset') {
    const iso = alarm.id === 'sunrise' ? day.sunrise_iso : day.sunset_iso;
    if (!iso) return [];
    return [{ start: new Date(iso), end: null, startText: clock(iso.slice(11, 16)), endText: null }];
  }
  const all: PanchangaWindow[] = [...day.windows.auspicious, ...day.windows.inauspicious];
  return all
    .filter((w) => w.name === alarm.window || w.name.startsWith(`${alarm.window} `))
    .map((w) => ({
      start: new Date(w.start_iso),
      end: new Date(w.end_iso),
      startText: clock(w.start),
      endText: clock(w.end),
    }));
}

function startNotification(alarm: PanchangAlarm, o: Occurrence, at: Date, exact: boolean): LocalNotificationSchema {
  const span = o.endText ? `${o.startText} – ${o.endText}` : o.startText;
  const title = alarm.lead === 0
    ? (o.endText ? `${alarm.title} now` : `${alarm.title} at ${o.startText}`)
    : `${alarm.title} in ${alarm.lead} minutes`;
  return {
    id: notificationId(`${alarm.id}:start:${o.start.toISOString()}`),
    title,
    body: `${span}. ${alarm.note}`,
    channelId: CHANNEL[alarm.style],
    smallIcon: 'ic_stat_siddha',
    schedule: { at, allowWhileIdle: true },
    isExactNotification: exact,
    foreground: alarm.style === 'alarm',
    autoCancel: true,
    extra: { kind: 'panchang', timing: alarm.id },
  };
}

function endNotification(alarm: PanchangAlarm, o: Occurrence, exact: boolean): LocalNotificationSchema {
  return {
    id: notificationId(`${alarm.id}:end:${o.start.toISOString()}`),
    title: `${alarm.title} is over`,
    body: `It ended at ${o.endText}.`,
    channelId: CHANNEL.silent,
    smallIcon: 'ic_stat_siddha',
    schedule: { at: o.end!, allowWhileIdle: true },
    isExactNotification: exact,
    autoCancel: true,
    extra: { kind: 'panchang', timing: alarm.id },
  };
}

/** A quiet note on the twelfth day: nothing tops the list up without the app. */
function keepGoingNote(timings: TimingsPayload, now: Date): LocalNotificationSchema | null {
  const day = timings.days[KEEP_GOING_DAY - 1];
  if (!day?.sunrise_iso) return null;
  // Mid-morning at the timing place: three hours after that day's sunrise.
  const at = new Date(new Date(day.sunrise_iso).getTime() + 3 * 60 * 60 * 1000);
  if (at <= now) return null;
  return {
    id: notificationId('keep-going'),
    title: 'Keep your panchang alarms going',
    body: 'Open Siddha to set your alarms for the next two weeks.',
    channelId: CHANNEL.silent,
    smallIcon: 'ic_stat_siddha',
    schedule: { at, allowWhileIdle: true },
    isExactNotification: false,
    autoCancel: true,
    extra: { kind: 'panchang', timing: 'keep-going' },
  };
}

/** A stable 32-bit id inside our range, from a string key. */
export function notificationId(key: string): number {
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (Math.imul(hash, 31) + key.charCodeAt(i)) | 0;
  return ID_BASE + (Math.abs(hash) % ID_SPAN);
}

function isOurs(id: number): boolean {
  return id >= ID_BASE && id < ID_BASE + ID_SPAN;
}

/** "16:42" → "4:42 pm". */
export function clock(hhmm: string): string {
  const [h, m] = hhmm.split(':').map(Number);
  if (Number.isNaN(h) || Number.isNaN(m)) return hhmm;
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`;
}

function restoreAlarms(): PanchangAlarm[] {
  try {
    const stored = JSON.parse(localStorage.getItem(ALARM_STORAGE_KEY) ?? '[]') as Partial<PanchangAlarm>[];
    return DEFAULT_ALARMS.map((alarm) => {
      const saved = stored.find((row) => row.id === alarm.id);
      return saved
        ? { ...alarm, on: saved.on ?? alarm.on, lead: saved.lead ?? alarm.lead, style: saved.style ?? alarm.style, atEnd: saved.atEnd ?? alarm.atEnd }
        : { ...alarm };
    });
  } catch {
    return DEFAULT_ALARMS.map((alarm) => ({ ...alarm }));
  }
}

function persistAlarms(alarms: PanchangAlarm[]): void {
  try {
    localStorage.setItem(
      ALARM_STORAGE_KEY,
      JSON.stringify(alarms.map(({ id, on, lead, style, atEnd }) => ({ id, on, lead, style, atEnd }))),
    );
  } catch {
    // Storage unavailable; the choice holds for this visit.
  }
}

function lastScheduled(): number {
  try {
    return Number(localStorage.getItem(SCHEDULED_KEY) ?? 0);
  } catch {
    return 0;
  }
}
