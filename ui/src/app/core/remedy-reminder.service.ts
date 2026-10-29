import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Capacitor } from '@capacitor/core';
import type { LocalNotificationSchema } from '@capacitor/local-notifications';

import { SessionTeardown } from './session-teardown';

/**
 * "Remedy reminders" in Settings > Notifications, as phone reminders.
 *
 * The switch had no sender (sweep 2026-10-29 G-2): mantra counts and streaks
 * live on the phone (mantra-tracker), so the server never knew a practice
 * was running. The practice screen records the last practice opened; while
 * the switch is on this schedules a 7 am reminder for it, weekly on its
 * preferred day (a Saturday mantra) or daily when it has none, and a tap
 * opens that practice. Nothing is scheduled for a practice not touched in
 * 30 days, so a reminder never nags about something the reader has left.
 */
export interface RemedyPractice {
  title: string;
  /** "Saturday", or null for a daily practice. */
  preferredDay: string | null;
  /** The practice screen's own route, e.g. /m/remedies/mantra?…. */
  route: string;
  updatedAt: string;
}

export const REMEDY_PRACTICE_KEY = 'siddha.remedyReminder:v1';
/** Settings > Notifications keeps its switches here (notifications.component.ts). */
const PREFS_KEY = 'astrospace.mobile.notificationPrefs';
const REMINDER_HOUR = 7;
const STALE_AFTER_DAYS = 30;
const DAILY_AHEAD = 14;
const WEEKLY_AHEAD = 6;
/** Beside the panchang alarms' range (1.7e9 to 1.8e9), never inside it. */
const ID_BASE = 1_800_000_000;
const ID_SPAN = 1_000;
const CHANNEL = 'siddha_windows';
const WEEKDAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

export function readPractice(): RemedyPractice | null {
  try {
    const value = JSON.parse(localStorage.getItem(REMEDY_PRACTICE_KEY) || 'null') as RemedyPractice | null;
    return value?.title && value.route?.startsWith('/m/') ? value : null;
  } catch {
    return null;
  }
}

function remindersOn(): boolean {
  try {
    const rows = JSON.parse(localStorage.getItem(PREFS_KEY) || '[]') as { id: string; on: boolean }[];
    return rows.find((row) => row.id === 'remedies')?.on ?? false;
  } catch {
    return false;
  }
}

/** The reminders for one practice from `now`. Pure, so the spec can check it without a phone. */
export function buildRemedyReminders(practice: RemedyPractice | null, now: Date): LocalNotificationSchema[] {
  if (!practice) return [];
  const touched = new Date(practice.updatedAt).getTime();
  if (!Number.isFinite(touched) || now.getTime() - touched > STALE_AFTER_DAYS * 86_400_000) return [];
  const weekday = WEEKDAYS.indexOf((practice.preferredDay ?? '').trim().toLowerCase());
  const out: LocalNotificationSchema[] = [];
  const day = new Date(now.getFullYear(), now.getMonth(), now.getDate(), REMINDER_HOUR, 0, 0, 0);
  if (day <= now) day.setDate(day.getDate() + 1);
  const wanted = weekday >= 0 ? WEEKLY_AHEAD : DAILY_AHEAD;
  for (let guard = 0; out.length < wanted && guard < 7 * WEEKLY_AHEAD + 7; guard += 1) {
    if (weekday < 0 || day.getDay() === weekday) {
      out.push({
        id: ID_BASE + out.length,
        title: 'Time for your practice',
        body: `${practice.title}. A few quiet minutes keeps your streak going.`,
        schedule: { at: new Date(day), allowWhileIdle: true },
        channelId: CHANNEL,
        extra: { kind: 'remedy', route: practice.route },
      });
    }
    day.setDate(day.getDate() + 1);
  }
  return out;
}

function isOurs(id: number): boolean {
  return id >= ID_BASE && id < ID_BASE + ID_SPAN;
}

@Injectable({ providedIn: 'root' })
export class RemedyReminderService {
  private readonly router = inject(Router);
  private readonly native = Capacitor.isNativePlatform();
  private started = false;

  constructor() {
    inject(SessionTeardown).register(() => {
      try { localStorage.removeItem(REMEDY_PRACTICE_KEY); } catch { /* storage unavailable */ }
      void this.cancelAll();
    });
  }

  /** Called once the app knows who is signed in (AppBoot). */
  async init(): Promise<void> {
    if (!this.native || this.started) return;
    this.started = true;
    try {
      const { LocalNotifications } = await import('@capacitor/local-notifications');
      await LocalNotifications.addListener('localNotificationActionPerformed', ({ notification }) => {
        const route = notification.extra?.kind === 'remedy' ? notification.extra.route : null;
        if (typeof route === 'string' && route.startsWith('/m/')) void this.router.navigateByUrl(route);
      });
    } catch {
      return;
    }
    await this.reschedule();
  }

  /** The practice screen calls this whenever a count or a completion is saved. */
  record(practice: Omit<RemedyPractice, 'updatedAt'>): void {
    try {
      localStorage.setItem(REMEDY_PRACTICE_KEY, JSON.stringify({ ...practice, updatedAt: new Date().toISOString() }));
    } catch {
      return;
    }
    void this.reschedule();
  }

  /** After the Settings switch changes, and on every record(). */
  async reschedule(): Promise<void> {
    if (!this.native) return;
    try {
      const { LocalNotifications } = await import('@capacitor/local-notifications');
      await this.cancelAll();
      if (!remindersOn()) return;
      const notifications = buildRemedyReminders(readPractice(), new Date());
      if (notifications.length) await LocalNotifications.schedule({ notifications });
    } catch {
      // No plugin, or no permission yet; the next open tries again.
    }
  }

  private async cancelAll(): Promise<void> {
    if (!this.native) return;
    try {
      const { LocalNotifications } = await import('@capacitor/local-notifications');
      const { notifications } = await LocalNotifications.getPending();
      const ours = notifications.filter((n) => isOurs(n.id));
      if (ours.length) await LocalNotifications.cancel({ notifications: ours.map((n) => ({ id: n.id })) });
    } catch {
      // Nothing pending, or the plugin is missing.
    }
  }
}
