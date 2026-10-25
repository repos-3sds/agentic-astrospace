import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { KundliStore } from '../../../core/kundli.store';
import { PanchangaDay } from '../../../core/models';
import { PanchangaService } from '../../../core/panchanga.service';
import { PreferencesService } from '../../../core/preferences.service';

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
  group: 'good' | 'careful';
  on: boolean;
  lead: AlarmLead;
  style: AlarmStyle;
  /** Also a short note when the timing is over. */
  atEnd: boolean;
}

/**
 * Settings — Panchang alarms.
 *
 * One switch per timing, each with its own "when" and "how". The alarms are
 * scheduled on the phone, not sent by the server, so they ring on time with
 * no internet and without the worker's 15-minute cadence.
 *
 * Defaults are deliberately few: Rahu Kalam and Abhijit only. Nobody gets a
 * 4:30 am alarm they did not ask for, so Brahma Muhurta starts off and
 * offers the "Alarm" style the moment it is turned on.
 *
 * Copy follows the notifications rule: an alarm says a timing is coming and
 * what it is good for, never what will go wrong in it.
 */
@Component({
  selector: 'as-settings-panchang-alarms',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, RouterLink],
  templateUrl: './panchang-alarms.component.html',
  styleUrl: './panchang-alarms.component.scss',
})
export class PanchangAlarmsComponent {
  private readonly panchanga = inject(PanchangaService);
  private readonly kundlis = inject(KundliStore);
  private readonly preferences = inject(PreferencesService);
  private readonly storageKey = 'astrospace.mobile.panchangAlarms';

  readonly leads: { value: AlarmLead; label: string }[] = [
    { value: 0, label: 'At start' },
    { value: 5, label: '5 min' },
    { value: 10, label: '10 min' },
    { value: 15, label: '15 min' },
    { value: 30, label: '30 min' },
  ];

  readonly styles: { value: AlarmStyle; label: string; detail: string }[] = [
    { value: 'alarm', label: 'Alarm', detail: 'Rings until you stop it, even on silent' },
    { value: 'bell', label: 'Bell', detail: 'One temple bell, like a notification' },
    { value: 'silent', label: 'Silent', detail: 'Shows on screen, no sound' },
  ];

  private readonly defaults: PanchangAlarm[] = [
    { id: 'brahma', window: 'Brahma Muhurta', title: 'Brahma Muhurta', detail: 'Before sunrise, for prayer and study', group: 'good', on: false, lead: 0, style: 'alarm', atEnd: false },
    { id: 'sunrise', window: null, title: 'Sunrise', detail: 'Morning sandhya and Surya namaskar', group: 'good', on: false, lead: 0, style: 'bell', atEnd: false },
    { id: 'abhijit', window: 'Abhijit Muhurta', title: 'Abhijit Muhurta', detail: 'Midday, good for important starts', group: 'good', on: true, lead: 0, style: 'bell', atEnd: false },
    { id: 'amrit', window: 'Amrit Kalam', title: 'Amrit Kalam', detail: 'A good window, moves every day', group: 'good', on: false, lead: 0, style: 'bell', atEnd: false },
    { id: 'godhuli', window: 'Godhuli', title: 'Godhuli', detail: 'Dusk, for lighting the lamp', group: 'good', on: false, lead: 0, style: 'bell', atEnd: false },
    { id: 'sunset', window: null, title: 'Sunset', detail: 'Evening sandhya', group: 'good', on: false, lead: 0, style: 'bell', atEnd: false },
    { id: 'rahu', window: 'Rahu Kalam', title: 'Rahu Kalam', detail: 'Pause new beginnings till it ends', group: 'careful', on: true, lead: 10, style: 'bell', atEnd: false },
    { id: 'yama', window: 'Yamaganda', title: 'Yamaganda', detail: 'Pause new starts and travel', group: 'careful', on: false, lead: 10, style: 'bell', atEnd: false },
    { id: 'gulika', window: 'Gulika Kalam', title: 'Gulika Kalam', detail: 'Pause new starts', group: 'careful', on: false, lead: 10, style: 'bell', atEnd: false },
    { id: 'durmuhurta', window: 'Durmuhurta', title: 'Durmuhurta', detail: 'Short times to keep clear of ceremonies', group: 'careful', on: false, lead: 10, style: 'silent', atEnd: false },
    { id: 'varjya', window: 'Varjya', title: 'Varjyam', detail: 'A careful window, moves every day', group: 'careful', on: false, lead: 10, style: 'silent', atEnd: false },
    { id: 'bhadra', window: 'Bhadra', title: 'Bhadra', detail: 'Keep clear of auspicious starts', group: 'careful', on: false, lead: 10, style: 'silent', atEnd: false },
  ];

  readonly alarms = signal<PanchangAlarm[]>(this.restore());
  /** The row whose "when" and "how" are open. One at a time. */
  readonly open = signal<string | null>(null);
  readonly day = signal<PanchangaDay | null>(null);

  readonly good = computed(() => this.alarms().filter((a) => a.group === 'good'));
  readonly careful = computed(() => this.alarms().filter((a) => a.group === 'careful'));
  readonly onCount = computed(() => this.alarms().filter((a) => a.on).length);
  readonly place = computed(
    () => this.preferences.panchangaPlace()?.label ?? this.day()?.place?.city ?? 'your city',
  );

  constructor() {
    void this.loadToday();
  }

  /** Today's time for a row, so the switch is never abstract. */
  protected todayTime(alarm: PanchangAlarm): string {
    const day = this.day();
    if (!day) return '';
    if (alarm.id === 'sunrise') return this.clock(day.sunrise);
    if (alarm.id === 'sunset') return this.clock(day.sunset);
    const all = [...day.windows.auspicious, ...day.windows.inauspicious];
    const match = all.find((w) => w.name === alarm.window || w.name.startsWith(`${alarm.window} `));
    return match ? `${this.clock(match.start)} – ${this.clock(match.end)}` : 'Not today';
  }

  protected summary(alarm: PanchangAlarm): string {
    const when = alarm.lead === 0 ? 'At start' : `${alarm.lead} min before`;
    const how = this.styles.find((s) => s.value === alarm.style)!.label;
    return `${when} · ${how}${alarm.atEnd ? ' · and at end' : ''}`;
  }

  protected toggle(id: string): void {
    const wasOn = this.alarms().find((a) => a.id === id)?.on;
    this.update(id, { on: !wasOn });
    this.open.set(wasOn ? (this.open() === id ? null : this.open()) : id);
  }

  protected expand(id: string): void {
    this.open.set(this.open() === id ? null : id);
  }

  protected setLead(id: string, lead: AlarmLead): void { this.update(id, { lead }); }
  protected setStyle(id: string, style: AlarmStyle): void { this.update(id, { style }); }
  protected toggleEnd(id: string): void {
    const alarm = this.alarms().find((a) => a.id === id);
    if (alarm) this.update(id, { atEnd: !alarm.atEnd });
  }

  private update(id: string, patch: Partial<PanchangAlarm>): void {
    this.alarms.update((all) => all.map((a) => (a.id === id ? { ...a, ...patch } : a)));
    this.persist();
  }

  private async loadToday(): Promise<void> {
    try {
      if (!this.kundlis.loaded()) await this.kundlis.load();
      const id = this.kundlis.owner()?.id ?? this.kundlis.active()?.id;
      if (id) this.day.set(await this.panchanga.today(id));
    } catch {
      // Times are a nicety on this screen; the switches work without them.
    }
  }

  /** "16:42" → "4:42 pm". */
  private clock(hhmm: string): string {
    const [h, m] = hhmm.split(':').map(Number);
    if (Number.isNaN(h) || Number.isNaN(m)) return hhmm;
    const suffix = h < 12 ? 'am' : 'pm';
    return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${suffix}`;
  }

  private restore(): PanchangAlarm[] {
    try {
      const stored = JSON.parse(localStorage.getItem(this.storageKey) ?? '[]') as Partial<PanchangAlarm>[];
      return this.defaults.map((alarm) => {
        const saved = stored.find((row) => row.id === alarm.id);
        return saved
          ? { ...alarm, on: saved.on ?? alarm.on, lead: saved.lead ?? alarm.lead, style: saved.style ?? alarm.style, atEnd: saved.atEnd ?? alarm.atEnd }
          : alarm;
      });
    } catch {
      return this.defaults;
    }
  }

  private persist(): void {
    try {
      localStorage.setItem(
        this.storageKey,
        JSON.stringify(this.alarms().map(({ id, on, lead, style, atEnd }) => ({ id, on, lead, style, atEnd }))),
      );
    } catch {
      // Storage unavailable; the choice holds for this visit.
    }
  }
}
