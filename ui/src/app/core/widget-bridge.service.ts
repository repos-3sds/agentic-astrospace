import { Injectable, Injector, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Capacitor, registerPlugin } from '@capacitor/core';
import { App as CapacitorApp } from '@capacitor/app';
import { ApiService } from './api.service';
import { FestivalPlace, FestivalService } from './festival.service';
import { CalendarDaySummary, DayQuality } from './models';
import { PanchangaService } from './panchanga.service';
import { NATURAL_VOICE_NAME, NaturalVoiceService, naturalChunks, prepareForSpeech } from './natural-voice.service';
import { PreferencesService } from './preferences.service';
import { SessionTeardown } from './session-teardown';
import { Subhashita, localIsoDate } from './subhashita.service';
import { noteDeepLink } from './deep-link-arrival';

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
  saveListenAudio(options: { date: string; text: string; parts: string[] }): Promise<void>;
  addListener(event: 'open', handler: (event: { route: string }) => void): Promise<{ remove(): Promise<void> }>;
}

/** Native side: ui/android/.../widgets/WidgetsPlugin.java. Android only for now. */
const SiddhaWidgets = registerPlugin<SiddhaWidgetsPlugin>('SiddhaWidgets');

interface MoonDaysPayload {
  is_convention_dependent?: boolean;
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
  /** The brief whose audio last went to the widget, so it isn't sent twice. */
  private listenAudioFor = '';

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

  /**
   * Siddha's own voice for the Listen widget. The widget can't sign in, so
   * the app hands it the same natural audio the Listen sheet plays: one MP3
   * per piece, only once the reader has played it in the app that day and it
   * is on the device. Making audio just to fill the widget cost a synthesis
   * on every open (cost fix, Hawk 2026-10-19), so until then, and when the
   * plan has no natural voice or the reader chose a phone voice, the widget
   * reads with the phone's voice, as before.
   */
  async publishListenAudio(date: string, text: string): Promise<void> {
    if (!this.enabled || !text.trim()) return;
    const key = `${date}\n${text}`;
    if (this.listenAudioFor === key) return;
    this.listenAudioFor = key;
    try {
      const chosen = this.injector.get(PreferencesService).voiceName();
      const voice = this.injector.get(NaturalVoiceService);
      if ((chosen !== null && chosen !== NATURAL_VOICE_NAME) || !(await voice.available())) {
        await SiddhaWidgets.saveListenAudio({ date, text, parts: [] });
        return;
      }
      const parts: string[] = [];
      for (const chunk of naturalChunks(text)) {
        const blob = await voice.cached(prepareForSpeech(chunk));
        if (!blob) {
          // Not listened to yet: phone voice for now, and look again next publish.
          await SiddhaWidgets.saveListenAudio({ date, text, parts: [] });
          this.listenAudioFor = '';
          return;
        }
        parts.push(await base64(blob));
      }
      await SiddhaWidgets.saveListenAudio({ date, text, parts });
    } catch {
      // Offline or the voice is down: try again on the next publish.
      this.listenAudioFor = '';
    }
  }

  publishSubhashita(days: readonly Subhashita[]): void {
    this.publish('subhashita', {
      days: days.map(({ date, sanskrit, english, meaning, source, ref }) => ({ date, sanskrit, english, meaning, source, ref })),
    });
  }

  /**
   * Festivals are the ones Today already loaded; moon days, vrat days and the
   * reader's day quality for the week are fetched here. Each date keeps
   * whether it depends on a convention (`approx`), so the widget line can say
   * so: there is no room for the full note, and the tap opens the calendar,
   * where it is shown. The week strip (CalendarWidget.java) tints each of the
   * next seven days good / take care exactly as the Calendar tab does, from
   * the same /panchanga/{id}/month, and shows each day's tithi from the
   * calendar Today already loaded.
   */
  async publishCalendar(
    place: FestivalPlace,
    fromDate: string,
    festivals: readonly { name: string; occurs_on: string; is_convention_dependent?: boolean }[],
    week?: { profileId: string; days: readonly CalendarDaySummary[] },
  ): Promise<void> {
    if (!this.enabled) return;
    const today = localIsoDate();
    const query = new URLSearchParams({ city: place.city, nation: place.nation, from_date: fromDate, days: '60' });
    const [moons, qualities, vrats] = await Promise.allSettled([
      this.injector.get(ApiService).get<MoonDaysPayload>(`/festivals/moon-days?${query}`),
      week ? this.injector.get(PanchangaService).month(week.profileId, today, 7) : Promise.reject(new Error('no profile')),
      this.injector.get(FestivalService).vratDays(place, today, 7),
    ]);
    // Each extra is optional: the festivals still go out, and the widget
    // shows a plain day where a tint or a vrat did not arrive.
    let moonDays: { date: string; moon: 'full' | 'new'; approx: boolean }[] = [];
    if (moons.status === 'fulfilled') {
      const approx = moons.value.is_convention_dependent !== false;
      moonDays = moons.value.moon_days.map((d) => ({ ...d, approx }));
    }
    this.publish('calendar', {
      festivals: festivals.map((f) => ({ date: f.occurs_on, name: f.name, approx: !!f.is_convention_dependent })),
      moonDays,
      vrats: vrats.status === 'fulfilled'
        ? vrats.value.days.map((v) => ({ date: v.date, name: v.name, approx: v.is_convention_dependent }))
        : [],
      days: weekDays(today, week?.days ?? [], qualities.status === 'fulfilled' ? qualities.value.days : []),
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
    if (isWidgetRoute(route)) {
      noteDeepLink();
      void this.router.navigateByUrl(route);
    }
  }
}

function base64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).replace(/^data:[^,]*,/, ''));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
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

/**
 * The calendar widget's seven days from `from`: each day's tithi and the
 * reader's day quality, where the app has them. Exported for the spec.
 */
export function weekDays(
  from: string,
  days: readonly Pick<CalendarDaySummary, 'date' | 'tithi'>[],
  qualities: readonly Pick<DayQuality, 'date' | 'quality'>[],
): { date: string; tithi: string; quality: DayQuality['quality'] | '' }[] {
  const tithi = new Map(days.map((d) => [d.date, d.tithi]));
  const quality = new Map(qualities.map((q) => [q.date, q.quality]));
  const [y, m, d] = from.split('-').map(Number);
  return Array.from({ length: 7 }, (_, i) => {
    const date = new Date(Date.UTC(y, m - 1, d + i)).toISOString().slice(0, 10);
    return { date, tithi: tithi.get(date) ?? '', quality: quality.get(date) ?? '' };
  });
}

/** Screens a widget opens. Exported for the spec. */
export const WIDGET_ROUTES = new Set(['/m/today', '/m/ask', '/m/calendar', '/m/remedies', '/m/subhashita']);
const MANTRA_PARAM = /^[\w-]{0,64}$/;

/**
 * MainActivity is exported (it is the launcher), so any installed app can
 * send it a `siddha_route` extra. Only the widgets' own screens pass, and
 * the mantra route only with its three id parameters (audit D15).
 */
export function isWidgetRoute(route: string | null | undefined): boolean {
  if (!route) return false;
  if (WIDGET_ROUTES.has(route)) return true;
  const [path, query = '', ...rest] = route.split('?');
  if (path !== '/m/remedies/mantra' || rest.length) return false;
  const params = new URLSearchParams(query);
  for (const [key, value] of params) {
    if (!['recommendation', 'practice', 'profile'].includes(key) || !MANTRA_PARAM.test(value)) return false;
  }
  return true;
}
