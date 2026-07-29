import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
import { ThemeService } from '../../../core/theme.service';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';
import { PreferencesService } from '../../../core/preferences.service';

/** One settings row. `value` is the current state, shown without opening it. */
export interface SettingRow {
  id: string;
  icon: string;
  label: string;
  value: string;
  /** Present once the destination exists; absent leaves the row inert. */
  route?: string[];
}

/** A titled group of rows. */
export interface SettingGroup {
  eyebrow: string;
  rows: SettingRow[];
}

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
      ?? 'Your space';
    return {
      initial: name.slice(0, 1).toUpperCase(),
      name,
      email: this.auth.email(),
    };
  });

  readonly groups = computed<SettingGroup[]>(() => [
    {
      eyebrow: 'EXPERIENCE',
      rows: [
        {
          id: 'appearance',
          icon: 'set-mode',
          label: 'Appearance',
          value: this.theme.preference()[0].toUpperCase() + this.theme.preference().slice(1),
          route: ['/m', 'settings', 'appearance'],
        },
        {
          id: 'mode',
          icon: `persona-${this.preferences.experienceMode()}`,
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
          icon: 'language',
          label: 'Language & audio',
          value: 'English · Audio on',
          route: ['/m', 'settings', 'language'],
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
          value: '3 on',
          route: ['/m', 'settings', 'notifications'],
        },
        {
          id: 'location',
          icon: this.preferences.panchangaPlace() ? 'pin-accent' : 'loc-current',
          label: 'Location',
          value: this.locationLabel(),
          route: ['/m', 'settings', 'location'],
        },
        {
          id: 'conventions',
          icon: 'chart-east',
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
          icon: 'shield',
          label: 'Account & privacy',
          value: 'Sign out, delete',
          route: ['/m', 'settings', 'account'],
        },
        {
          id: 'notification-center',
          icon: 'set-notif',
          label: 'Notification center',
          value: 'Recent updates',
          route: ['/m', 'notifications'],
        },
        {
          id: 'subscription',
          icon: 'sparkle',
          label: 'AstroSpace Plus',
          value: 'View plans',
          route: ['/m', 'subscription'],
        },
      ],
    },
  ]);

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

  private locationLabel(): string {
    const place = this.preferences.panchangaPlace();
    if (place?.city) return place.city;
    const timezone = this.preferences.browserTimezone().split('/').pop()?.replaceAll('_', ' ');
    return timezone ? `Current · ${timezone}` : 'Current location';
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
}
