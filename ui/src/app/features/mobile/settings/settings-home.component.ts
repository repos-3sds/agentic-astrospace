import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { App as CapacitorApp } from '@capacitor/app';
import { Capacitor } from '@capacitor/core';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
import { LegalDocument, openLegal } from '../../../core/legal';
import { ThemeService } from '../../../core/theme.service';
import { TextSizeService } from '../../../core/text-size.service';
import { EntitlementService } from '../../../core/entitlement.service';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { PreferencesService } from '../../../core/preferences.service';
import { NATURAL_VOICE_NAME, NaturalVoiceService } from '../../../core/natural-voice.service';
import { plannedTimingPlace } from '../../../core/timing-place';

/** One settings row. `value` is the current state, shown without opening it. */
export interface SettingRow {
  id: string;
  icon: string;
  label: string;
  value: string;
  /** Present once the destination exists; absent leaves the row inert. */
  route?: string[];
  /** A legal page served by the API, opened outside the SPA. */
  legal?: LegalDocument;
}

/** A titled group of rows. */
export interface SettingGroup {
  eyebrow: string;
  rows: SettingRow[];
}

const NOTIFICATION_STORAGE_KEY = 'astrospace.mobile.notificationPrefs';
const ALARM_STORAGE_KEY = 'astrospace.mobile.panchangAlarms';

/**
 * Settings — Home (Figma node 66:89), the fifth tab in every mode.
 *
 * Every row states its current value on the right, so the common question —
 * "which ayanamsha am I on?" — is answered by looking rather than by opening
 * six screens. That matters most for Conventions: the reading changes when it
 * changes, and a convention you have to go hunting for is one you will forget
 * you set.
 */
@Component({
  selector: 'as-settings-home',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ProfileSwitcherComponent],
  templateUrl: './settings-home.component.html',
  styleUrl: './settings-home.component.scss',
})
export class SettingsHomeComponent {
  private readonly auth = inject(AuthService);
  private readonly kundlis = inject(KundliStore);
  private readonly theme = inject(ThemeService);
  private readonly textSize = inject(TextSizeService);
  private readonly preferences = inject(PreferencesService);
  private readonly entitlements = inject(EntitlementService);
  readonly profileSwitcherOpen = signal(false);

  readonly profile = computed(() => {
    const name = this.kundlis.active()?.name
      ?? this.auth.user()?.user_metadata?.['name']
      ?? 'Your path';
    return {
      initial: name.slice(0, 1).toUpperCase(),
      name,
      email: this.auth.email(),
    };
  });

  /**
   * Six plainly named sections, most-used first (Hawk, 2026-10-20). Labels
   * say what a row changes rather than the engine's word for it: "Chart
   * method", not "Conventions"; "Vibration", not "Interaction".
   */
  readonly groups = computed<SettingGroup[]>(() => [
    {
      eyebrow: 'YOU AND YOUR FAMILY',
      rows: [
        {
          id: 'family',
          icon: 'nav-family',
          label: 'Family',
          value: 'Switch person, add someone',
          route: ['/m', 'family'],
        },
        {
          id: 'profiles',
          icon: 'set-profiles',
          label: 'Manage profiles',
          value: `${this.kundlis.kundlis().length} saved · edit or remove`,
          route: ['/m', 'settings', 'profiles'],
        },
        {
          id: 'memory',
          icon: 'set-inbox',
          label: 'What Siddha remembers',
          value: !this.preferences.memoryEnabled()
            ? 'Off'
            : this.preferences.memoryMode() === 'automatic' ? 'Saves details on its own' : 'Asks before saving',
          route: this.kundlis.active()?.id
            ? ['/m', 'settings', 'profiles', this.kundlis.active()!.id, 'memory']
            : ['/m', 'settings', 'profiles'],
        },
      ],
    },
    {
      eyebrow: 'YOUR PLAN',
      rows: [
        {
          id: 'subscription',
          icon: 'set-plus',
          label: 'Plan and purchases',
          value: this.planLabel(),
          route: ['/m', 'subscription'],
        },
      ],
    },
    {
      eyebrow: 'ALERTS',
      rows: [
        {
          id: 'notifications',
          icon: 'set-notif',
          label: 'Notifications and emails',
          value: this.notificationLabel(),
          route: ['/m', 'settings', 'notifications'],
        },
        {
          id: 'alarms',
          icon: 'set-notif',
          label: 'Panchang alarms',
          value: this.alarmLabel(),
          route: ['/m', 'settings', 'alarms'],
        },
      ],
    },
    {
      eyebrow: 'LOOK AND FEEL',
      rows: [
        {
          id: 'appearance',
          icon: 'set-appearance',
          label: 'Light or dark',
          value: this.themeLabel(),
          route: ['/m', 'settings', 'appearance'],
        },
        ...(this.textSize.available ? [{
          id: 'text-size',
          icon: 'set-text',
          label: 'Text size',
          value: this.textSizeLabel(),
          route: ['/m', 'settings', 'text-size'],
        }] : []),
        {
          id: 'language',
          icon: 'set-lang',
          label: 'Language and voice',
          value: `${this.languageLabel()} · ${this.preferences.readAloud() ? this.voiceLabel() : 'Listen off'}`,
          route: ['/m', 'settings', 'language'],
        },
        {
          id: 'interaction',
          icon: 'set-interaction',
          label: 'Vibration',
          value: this.preferences.hapticsEnabled() ? 'On for taps' : 'Off',
          route: ['/m', 'settings', 'interaction'],
        },
      ],
    },
    {
      eyebrow: 'READINGS AND ASTROLOGY',
      rows: [
        {
          id: 'mode',
          icon: 'set-tone',
          label: 'Detail and tone',
          value: `${this.modeLabel()} · ${this.toneLabel()}`,
          route: ['/m', 'settings', 'mode'],
        },
        {
          id: 'location',
          icon: 'set-loc',
          label: 'City for timings',
          value: this.locationLabel(),
          route: ['/m', 'settings', 'location'],
        },
        {
          id: 'festivals',
          icon: 'set-festival',
          label: 'Festivals to show',
          value: this.festivalLabel(),
          route: ['/m', 'settings', 'festivals'],
        },
        {
          id: 'conventions',
          icon: 'set-conv',
          label: 'Chart method',
          value: `${this.ayanamshaLabel()} · ${this.chartStyleLabel()} chart`,
          route: ['/m', 'settings', 'conventions'],
        },
      ],
    },
    {
      eyebrow: 'ACCOUNT AND PRIVACY',
      rows: [
        {
          id: 'account',
          icon: 'set-account',
          label: 'Account',
          value: 'Email, your data, sign out, delete',
          route: ['/m', 'settings', 'account'],
        },
        { id: 'terms', icon: 'set-legal', label: 'Terms of Service', value: 'Opens in your browser', legal: 'terms' },
        { id: 'privacy', icon: 'set-legal', label: 'Privacy Policy', value: 'Opens in your browser', legal: 'privacy' },
      ],
    },
  ]);

  protected openLegal(doc: LegalDocument): void {
    void openLegal(doc);
  }

  /** Whether Listen will use Siddha's natural voice; false until known. */
  private readonly naturalAvailable = signal(false);

  /** "1.0.0 (build 488)" on the phone, so a bug report can say which build. */
  protected readonly appVersion = signal<string | null>(null);

  constructor() {
    if (!this.kundlis.loaded()) void this.kundlis.load().catch(() => undefined);
    void this.textSize.load();
    if (Capacitor.isNativePlatform()) {
      void CapacitorApp.getInfo()
        .then((info) => this.appVersion.set(`${info.version} (build ${info.build})`))
        .catch(() => undefined);
    }
    void inject(NaturalVoiceService).available().then((ok) => this.naturalAvailable.set(ok)).catch(() => undefined);
  }

  /** The plan by name once the server has said; never a guessed "Free". */
  private planLabel(): string {
    const tier = this.entitlements.current()?.access_tier;
    const name = tier === 'pro' ? 'Practitioner' : tier === 'plus' ? 'Plus' : tier === 'free' ? 'Free' : null;
    return name ? `${name} · see plans, buy questions` : 'See plans, buy questions';
  }

  private textSizeLabel(): string {
    const choice = this.textSize.choice();
    return choice === 90 ? 'Small' : choice === 100 ? 'Standard' : choice === 115 ? 'Large'
      : choice === 130 ? 'Extra large' : 'Same as phone';
  }

  private themeLabel(): string {
    const theme = this.theme.preference();
    return theme === 'system' ? 'Same as phone' : theme === 'dark' ? 'Dark' : 'Light';
  }

  private modeLabel(): string {
    const mode = this.preferences.experienceMode();
    return mode === 'guided' ? 'Guided' : mode === 'practitioner' ? 'Practitioner' : 'Balanced';
  }

  private toneLabel(): string {
    return this.preferences.tone() === 'direct' ? 'Direct' : 'Gentle';
  }

  /** The voice Listen will use; there is no on/off, so never say "on". */
  private voiceLabel(): string {
    const name = this.preferences.voiceName();
    // Automatic (null) means the natural voice when the plan has it; this row
    // said "Default voice" while Listen used it (regression 2026-10-17).
    if (name === NATURAL_VOICE_NAME || (name == null && this.naturalAvailable())) return 'Siddha natural voice';
    if (!name) return 'Phone voice';
    // Device voice names carry vendor noise: "Google हिन्दी (India)", "en-in-x-ene-local".
    const short = name.replace(/\s*\(.*\)\s*$/, '').trim();
    return short.length > 18 ? 'Chosen voice' : short;
  }

  private languageLabel(): string {
    return this.preferences.language() === 'te' ? 'Telugu' : 'English';
  }

  private locationLabel(): string {
    return plannedTimingPlace(this.preferences.panchangaPlace(), this.preferences.browserTimezone()).short;
  }

  private ayanamshaLabel(): string {
    const value = this.preferences.ayanamsha();
    if (value === 'krishnamurti') return 'KP';
    return value.slice(0, 1).toUpperCase() + value.slice(1);
  }

  private chartStyleLabel(): string {
    const value = this.preferences.chartStyle();
    if (value === 'south') return 'South';
    if (value === 'north') return 'North';
    return 'Eastern';
  }

  private festivalLabel(): string {
    const regions = this.preferences.festivalRegions();
    if (regions.length >= 3) return 'Multi-ethnic';
    return regions.map((region) =>
      region === 'pan-india' ? 'Essentials' : region === 'south' ? 'South' : 'North',
    ).join(' · ') || 'Essentials';
  }

  private notificationLabel(): string {
    try {
      const stored = JSON.parse(localStorage.getItem(NOTIFICATION_STORAGE_KEY) ?? '[]') as Array<{ id: string; on: boolean }>;
      if (!stored.length) return 'Daily reading, festivals, reminders';
      const onCount = stored.filter((row) => row.on).length;
      return onCount ? `${onCount} turned on` : 'All off';
    } catch {
      return 'Daily reading, festivals, reminders';
    }
  }

  private alarmLabel(): string {
    try {
      const stored = JSON.parse(localStorage.getItem(ALARM_STORAGE_KEY) ?? '[]') as Array<{ on: boolean }>;
      if (!stored.length) return 'Rahu Kalam, Abhijit';
      const onCount = stored.filter((row) => row.on).length;
      return onCount ? `${onCount} turned on` : 'All off';
    } catch {
      return 'Rahu Kalam, Abhijit';
    }
  }
}
