import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { KundliStore } from '../../../core/kundli.store';
import { PanchangaDay } from '../../../core/models';
import {
  AlarmLead,
  AlarmStyle,
  PanchangAlarm,
  PanchangAlarmService,
  clock,
} from '../../../core/panchang-alarm.service';
import { PanchangaService } from '../../../core/panchanga.service';
import { PreferencesService } from '../../../core/preferences.service';
import { PushService } from '../../../core/push.service';

const EXACT_ASKED_KEY = 'astrospace.mobile.panchangAlarms.exactAsked';

/**
 * Settings — Panchang alarms.
 *
 * One switch per timing, each with its own "when" and "how". The alarms are
 * scheduled on the phone (PanchangAlarmService), not sent by the server, so
 * they ring on time with no internet.
 *
 * Defaults are deliberately few: Rahu Kalam and Abhijit only. Nobody gets a
 * 4:30 am alarm they did not ask for, so Brahma Muhurta starts off and
 * carries the "Alarm" style the moment it is turned on.
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
  private readonly service = inject(PanchangAlarmService);
  private readonly panchanga = inject(PanchangaService);
  private readonly kundlis = inject(KundliStore);
  private readonly preferences = inject(PreferencesService);
  private readonly push = inject(PushService);

  readonly leads: { value: AlarmLead; label: string }[] = [
    { value: 0, label: 'At start' },
    { value: 5, label: '5 min' },
    { value: 10, label: '10 min' },
    { value: 15, label: '15 min' },
    { value: 30, label: '30 min' },
  ];

  readonly styles: { value: AlarmStyle; label: string; detail: string }[] = [
    { value: 'alarm', label: 'Alarm', detail: 'Rings for 30 seconds, even on silent' },
    { value: 'bell', label: 'Bell', detail: 'One temple bell, like a notification' },
    { value: 'silent', label: 'Silent', detail: 'Shows on screen, no sound' },
  ];

  readonly alarms = this.service.alarms;
  readonly error = this.service.error;
  readonly native = this.service.native;
  /** The row whose "when" and "how" are open. One at a time. */
  readonly open = signal<string | null>(null);
  readonly day = signal<PanchangaDay | null>(null);

  readonly good = computed(() => this.alarms().filter((a) => a.group === 'good'));
  readonly careful = computed(() => this.alarms().filter((a) => a.group === 'careful'));
  readonly anyOn = computed(() => this.alarms().some((a) => a.on));
  readonly place = computed(
    () => this.preferences.panchangaPlace()?.label ?? this.day()?.place?.city ?? 'your city',
  );

  /** Alarms cannot show while the phone blocks Siddha's notifications. */
  readonly blocked = computed(
    () => this.service.native && this.anyOn() && ['prompt', 'denied'].includes(this.push.permission()),
  );
  /** Android 12+: without "Alarms and reminders" they can run a few minutes late. */
  readonly inexact = computed(() => this.anyOn() && this.service.exact() === 'denied');
  readonly busy = signal(false);

  constructor() {
    void this.loadToday();
    void this.service.refreshExact();
    void this.push.refreshPermission();
  }

  /** Today's time for a row, so the switch is never abstract. */
  protected todayTime(alarm: PanchangAlarm): string {
    const day = this.day();
    if (!day) return '';
    if (alarm.id === 'sunrise') return clock(day.sunrise);
    if (alarm.id === 'sunset') return clock(day.sunset);
    const all = [...day.windows.auspicious, ...day.windows.inauspicious];
    const match = all.find((w) => w.name === alarm.window || w.name.startsWith(`${alarm.window} `));
    return match ? `${clock(match.start)} – ${clock(match.end)}` : 'Not today';
  }

  protected summary(alarm: PanchangAlarm): string {
    const when = alarm.lead === 0 ? 'At start' : `${alarm.lead} min before`;
    const how = this.styles.find((s) => s.value === alarm.style)!.label;
    return `${when} · ${how}${alarm.atEnd ? ' · and at end' : ''}`;
  }

  /**
   * Flips one switch and nothing else. Turning one on used to open its
   * "when" and "how" and close any other, so every row below jumped by the
   * editor's height under the reader's thumb: the next tap landed on a
   * different row, and switches seemed to turn on and off by themselves
   * (Deepak, 2026-10-28). The editor opens only from tapping the row.
   */
  protected toggle(id: string): void {
    const wasOn = this.alarms().find((a) => a.id === id)?.on;
    this.service.update(id, { on: !wasOn });
    if (wasOn && this.open() === id) this.open.set(null);
    if (!wasOn) void this.askOnce();
  }

  protected expand(id: string): void {
    this.open.set(this.open() === id ? null : id);
  }

  protected setLead(id: string, lead: AlarmLead): void { this.service.update(id, { lead }); }
  protected setStyle(id: string, style: AlarmStyle): void { this.service.update(id, { style }); }
  protected toggleEnd(id: string): void {
    const alarm = this.alarms().find((a) => a.id === id);
    if (alarm) this.service.update(id, { atEnd: !alarm.atEnd });
  }

  protected async enableNotifications(): Promise<void> {
    this.busy.set(true);
    try {
      await this.push.enable();
    } finally {
      this.busy.set(false);
    }
    void this.service.reschedule(true);
  }

  protected allowExact(): void {
    void this.service.requestExact();
  }

  /**
   * The first switch turned on asks for what alarms need: notifications, then
   * exact timing. Once each; after that the cards on the screen do the asking.
   */
  private async askOnce(): Promise<void> {
    if (!this.service.native) return;
    if (this.push.permission() === 'prompt') {
      await this.enableNotifications();
      return;
    }
    try {
      if (localStorage.getItem(EXACT_ASKED_KEY)) return;
      localStorage.setItem(EXACT_ASKED_KEY, '1');
    } catch {
      return;
    }
    await this.service.refreshExact();
    if (this.service.exact() === 'denied') await this.service.requestExact();
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
}
