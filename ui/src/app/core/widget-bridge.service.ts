import { Injectable, Injector, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Capacitor, registerPlugin } from '@capacitor/core';
import { App as CapacitorApp } from '@capacitor/app';
import { ApiService } from './api.service';
import { FestivalPlace } from './festival.service';
import { SessionTeardown } from './session-teardown';
import { Subhashita, localIsoDate } from './subhashita.service';

/**
 * What the home-screen widgets show, as the app last saw it. Each part is
 * stored on the phone (ui/android/.../widgets/WidgetStore.java) so the
 * widgets draw without the app running; the field names are read there.
 */
export interface TodayWidgetPart {
  /** The day the reading is for; widgets show nothing stale past it. */
  date: string;
  score: number;
  band: 'steady' | 'mixed' | 'tough';
  label: string;
  headline: string;
  summary: string;
  doItem: string;
  avoidItem: string;
  tithi: string;
  nakshatra: string;
  windows: { name: string; kind: string; startMs: number; endMs: number }[];
  /** What the Listen widget reads aloud: the same script as the Listen sheet. */
  listen: string;
}

export interface MantraWidgetPart {
  /** The tracker's storage key, so widget taps land on the same count. */
  key: string;
  title: string;
  target: number;
  count: number;
  date: string;
  route: string;
}

interface MantraTaps {
  key: string;
  date: string;
  taps: number;
}

interface SiddhaWidgetsPlugin {
  publish(options: { part: string; data: object }): Promise<void>;
  takeMantraTaps(): Promise<MantraTaps>;
  clear(): Promise<void>;
  takePendingRoute(): Promise<{ route: string }>;
  addListener(event: 'open', handler: (event: { route: string }) => void): Promise<{ remove(): Promise<void> }>;
}

/** Native side: ui/android/.../widgets/WidgetsPlugin.java. Android only for now. */
const SiddhaWidgets = registerPlugin<SiddhaWidgetsPlugin>('SiddhaWidgets');

interface MoonDaysPayload {
  moon_days: { date: string; moon: 'full' | 'new' }[];
}

/**
 * Keeps the Android home-screen widgets in step with the app: Today publishes
 * the owner's day, the tracker publishes the practice last opened, and the
 * verses and calendar go out as the app loads them. Every call is a no-op off
 * Android, and a failure never reaches the screen that made it.
 */
@Injectable({ providedIn: 'root' })
export class WidgetBridgeService {
  // Resolved on first use: off Android nothing here needs the network.
  private readonly injector = inject(Injector);
  private readonly router = inject(Router);
  private readonly teardown = inject(SessionTeardown);
  private started = false;

  readonly enabled = Capacitor.getPlatform() === 'android';
  /** Bumped when widget taps land in a stored practice, so an open tracker re-reads it. */
  readonly mantraTapsFolded = signal(0);

  /** Once, from the mobile shell: widget taps open their screen, and sign-out wipes the widgets. */
  start(): void {
    if (!this.enabled || this.started) return;
    this.started = true;
    void SiddhaWidgets.addListener('open', ({ route }) => this.go(route)).catch(() => undefined);
    void SiddhaWidgets.takePendingRoute().then(({ route }) => this.go(route)).catch(() => undefined);
    void this.foldMantraTaps();
    void CapacitorApp.addListener('appStateChange', ({ isActive }) => {
      if (isActive) void this.foldMantraTaps();
    }).catch(() => undefined);
    this.teardown.register(() => void SiddhaWidgets.clear().catch(() => undefined));
  }

  publishToday(part: TodayWidgetPart): void {
    this.publish('today', part);
  }

  publishSubhashita(days: readonly Subhashita[]): void {
    this.publish('subhashita', {
      days: days.map(({ date, sanskrit, english, meaning, source, ref }) => ({ date, sanskrit, english, meaning, source, ref })),
    });
  }

  /** Festivals are the ones Today already loaded; moon days are fetched here. */
  async publishCalendar(place: FestivalPlace, fromDate: string, festivals: readonly { name: string; occurs_on: string }[]): Promise<void> {
    if (!this.enabled) return;
    let moonDays: MoonDaysPayload['moon_days'] = [];
    try {
      const query = new URLSearchParams({ city: place.city, nation: place.nation, from_date: fromDate, days: '60' });
      moonDays = (await this.injector.get(ApiService).get<MoonDaysPayload>(`/festivals/moon-days?${query}`)).moon_days;
    } catch {
      // The festivals still go out; the moon widget waits for the next try.
    }
    this.publish('calendar', {
      festivals: festivals.map((f) => ({ date: f.occurs_on, name: f.name })),
      moonDays,
    });
  }

  publishMantra(part: MantraWidgetPart): void {
    this.publish('mantra', part);
  }

  /**
   * Counts made on the widget's ring go into the tracker's own record, so the
   * screen and the widget show one count. Only today's taps count: a ring
   * tapped yesterday and never opened is yesterday's practice.
   */
  async foldMantraTaps(): Promise<void> {
    if (!this.enabled) return;
    try {
      const taps = await SiddhaWidgets.takeMantraTaps();
      if (!taps.key || taps.taps <= 0 || taps.date !== localIsoDate()) return;
      applyMantraTaps(taps.key, taps.taps, taps.date);
      this.mantraTapsFolded.update((n) => n + 1);
    } catch {
      // Nothing to fold, or storage is unavailable.
    }
  }

  private publish(part: string, data: object): void {
    if (!this.enabled) return;
    void SiddhaWidgets.publish({ part, data }).catch(() => undefined);
  }

  private go(route: string): void {
    if (route?.startsWith('/m/')) void this.router.navigateByUrl(route);
  }
}

/** The mantra tracker's stored record (mantra-tracker.component.ts). */
export interface StoredPractice {
  count?: number;
  completedDates?: string[];
  date?: string;
  target?: number;
  updatedAt?: string;
}

/** Adds widget taps to a stored practice, completing the day at its target. */
export function applyMantraTaps(key: string, taps: number, date: string): void {
  const stored = (JSON.parse(localStorage.getItem(key) || 'null') ?? {}) as StoredPractice;
  const target = stored.target ?? 108;
  const base = stored.date === date ? stored.count ?? 0 : 0;
  const count = Math.min(target, base + taps);
  const dates = stored.completedDates ?? [];
  localStorage.setItem(key, JSON.stringify({
    ...stored,
    count,
    date,
    completedDates: count >= target && !dates.includes(date) ? [...dates, date] : dates,
    updatedAt: new Date().toISOString(),
  }));
}

/**
 * A wall-clock time in a place's timezone ("14:30" on 2026-10-17 in
 * Asia/Kolkata) as epoch milliseconds, so the widget's countdown is right
 * wherever the phone is.
 */
export function wallClockToEpoch(date: string, time: string, timeZone: string): number {
  const [y, mo, d] = date.split('-').map(Number);
  const [h, mi] = time.trim().split(':').map(Number);
  const asUtc = Date.UTC(y, mo - 1, d, h, mi);
  // The zone's offset at that moment, read back through Intl; twice, so a
  // time just across a DST change settles on the right side.
  let guess = asUtc - zoneOffset(asUtc, timeZone);
  guess = asUtc - zoneOffset(guess, timeZone);
  return guess;
}

function zoneOffset(epoch: number, timeZone: string): number {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone, hourCycle: 'h23',
    year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric',
  }).formatToParts(new Date(epoch));
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value ?? 0);
  const wall = Date.UTC(get('year'), get('month') - 1, get('day'), get('hour'), get('minute'), get('second'));
  return wall - Math.floor(epoch / 1000) * 1000;
}

/** "06:10–07:40" as two epoch times on the reading's day; an end past midnight rolls over. */
export function windowSpan(date: string, time: string, timeZone: string): { startMs: number; endMs: number } | null {
  const [start, end] = time.split(/[–-]/);
  if (!start || !end || !/\d:\d/.test(start) || !/\d:\d/.test(end)) return null;
  const startMs = wallClockToEpoch(date, start, timeZone);
  let endMs = wallClockToEpoch(date, end, timeZone);
  if (endMs <= startMs) endMs += 86_400_000;
  return { startMs, endMs };
}
