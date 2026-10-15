import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
import { LegalDocument, openLegal } from '../../../core/legal';
import { ThemeService } from '../../../core/theme.service';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { PreferencesService } from '../../../core/preferences.service';
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

/**
 * Settings — Home (Figma node 66:89), the More tab's destination.
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
  private readonly preferences = inject(PreferencesService);
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
   * Ask-first modes take the chart screens off the tab bar (checklist D1);
   * this is where they are listed instead. Practitioner keeps them as tabs,
   * so the group would only repeat the bar there.
   */
  private readonly chartGroup = computed<SettingGroup[]>(() => {
    const mode = this.preferences.experienceMode();
    if (mode === 'practitioner') return [];
    const rows: SettingRow[] = [];
    if (mode === 'guided') {
      rows.push({ id: 'explore', icon: 'explore-readings', label: 'Life guidance', value: 'Story, chapters', route: ['/m', 'explore'] });
    }
    rows.push(
      { id: 'chart', icon: 'explore-varga', label: 'Your chart', value: this.kundlis.active()?.ascendant ? `${this.kundlis.active()!.ascendant} rising` : 'Chart & vargas', route: ['/m', 'chart'] },
      { id: 'periods', icon: 'explore-dasha', label: 'Life periods', value: 'Dashas', route: ['/m', 'chart', 'periods'] },
      { id: 'transits', icon: 'explore-transit', label: 'Transits', value: 'Now', route: ['/m', 'transits'] },
      { id: 'readings', icon: 'explore-reference', label: 'Readings', value: 'Track record', route: ['/m', 'readings'] },
    );
    return [{ eyebrow: 'CHART & TIMING', rows }];
  });

  readonly groups = computed<SettingGroup[]>(() => [
    ...this.chartGroup(),
    {
      eyebrow: 'EXPERIENCE',
      rows: [
        {
          id: 'memory',
          icon: 'set-profiles',
          label: 'Memory',
          value: !this.preferences.memoryEnabled()
            ? 'Off'
            : this.preferences.memoryMode() === 'automatic' ? 'Automatic' : 'Ask every time',
          route: this.kundlis.active()?.id
            ? ['/m', 'settings', 'profiles', this.kundlis.active()!.id, 'memory']
            : ['/m', 'settings', 'profiles'],
        },
        {
          id: 'appearance',
          icon: 'set-appearance',
          label: 'Appearance',
          value: this.theme.preference()[0].toUpperCase() + this.theme.preference().slice(1),
          route: ['/m', 'settings', 'appearance'],
        },
        {
          id: 'mode',
          icon: 'set-tone',
          label: 'Mode & tone',
          value: `${this.modeLabel()} · ${this.toneLabel()}`,
          route: ['/m', 'settings', 'mode'],
        },
      ],
    },
    {
      eyebrow: 'LANGUAGE & AUDIO',
      rows: [
        {
          id: 'language',
          icon: 'set-lang',
          label: 'Language & audio',
          value: `${this.languageLabel()} · ${this.preferences.readAloud() ? this.voiceLabel() : 'Listen off'}`,
          route: ['/m', 'settings', 'language'],
        },
        {
          id: 'interaction',
          icon: 'set-interaction',
          label: 'Interaction',
          value: this.preferences.hapticsEnabled() ? 'Haptics on' : 'Haptics off',
          route: ['/m', 'settings', 'interaction'],
        },
      ],
    },
    {
      eyebrow: 'NOTIFICATIONS, LOCATION & CONVENTIONS',
      rows: [
        {
          id: 'notifications',
          icon: 'set-notif',
          label: 'Notifications',
          value: this.notificationLabel(),
          route: ['/m', 'settings', 'notifications'],
        },
        {
          id: 'location',
          icon: 'set-loc',
          label: 'Location',
          value: this.locationLabel(),
          route: ['/m', 'settings', 'location'],
        },
        // Festival regions tune the Calendar tab, which only Practitioner has.
        ...(this.preferences.experienceMode() === 'practitioner' ? [{
          id: 'festivals',
          icon: 'set-festival',
          label: 'Festival calendar',
          value: this.festivalLabel(),
          route: ['/m', 'settings', 'festivals'],
        }] : []),
        {
          id: 'conventions',
          icon: 'set-conv',
          label: 'Conventions',
          value: `${this.ayanamshaLabel()} · ${this.chartStyleLabel()}`,
          route: ['/m', 'settings', 'conventions'],
        },
      ],
    },
    {
      eyebrow: 'PROFILES',
      rows: [
        {
          id: 'profiles',
          icon: 'set-profiles',
          label: 'Manage profiles',
          value: `${this.kundlis.kundlis().length} ${this.kundlis.kundlis().length === 1 ? 'profile' : 'profiles'}`,
          route: ['/m', 'settings', 'profiles'],
        },
      ],
    },
    {
      eyebrow: 'ACCOUNT & PRIVACY',
      rows: [
        {
          id: 'account',
          icon: 'set-account',
          label: 'Account & privacy',
          value: 'Sign out, delete',
          route: ['/m', 'settings', 'account'],
        },
        {
          id: 'notification-center',
          icon: 'set-inbox',
          label: 'Notification center',
          value: 'Recent updates',
          route: ['/m', 'notifications'],
        },
        {
          id: 'subscription',
          icon: 'set-plus',
          label: 'Plans',
          value: 'Access and billing',
          route: ['/m', 'subscription'],
        },
      ],
    },
    {
      eyebrow: 'ABOUT',
      rows: [
        { id: 'terms', icon: 'set-legal', label: 'Terms of Service', value: 'Opens in browser', legal: 'terms' },
        { id: 'privacy', icon: 'set-legal', label: 'Privacy Policy', value: 'Opens in browser', legal: 'privacy' },
      ],
    },
  ]);

  protected openLegal(doc: LegalDocument): void {
    void openLegal(doc);
  }

  constructor() {
    if (!this.kundlis.loaded()) void this.kundlis.load().catch(() => undefined);
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
    if (!name) return 'Default voice';
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
      if (!stored.length) return 'Choose alerts';
      const onCount = stored.filter((row) => row.on).length;
      return `${onCount} selected`;
    } catch {
      return 'Choose alerts';
    }
  }
}
