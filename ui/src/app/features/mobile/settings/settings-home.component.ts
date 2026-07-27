import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';

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
          id: 'mode',
          icon: 'set-mode',
          label: 'Mode & tone',
          value: 'Balanced · Gentle',
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
          icon: 'set-loc',
          label: 'Location',
          value: 'Birth place',
          route: ['/m', 'settings', 'location'],
        },
        {
          id: 'conventions',
          icon: 'set-conv',
          label: 'Conventions',
          value: 'Lahiri · Eastern',
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
          route: ['/m', 'settings', 'birth-details'],
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
      ],
    },
  ]);

  constructor() {
    if (!this.kundlis.loaded()) void this.kundlis.load().catch(() => undefined);
  }
}
