import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
import { ProfileSwitcherComponent } from '../profile-switcher/profile-switcher.component';

interface ExploreCard {
  title: string;
  body: string;
  route: string[];
  icon: string;
  tone: 'gold' | 'good' | 'accent';
}

@Component({
  selector: 'as-guided-explore',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ProfileSwitcherComponent, RouterLink],
  templateUrl: './guided-explore.component.html',
  styleUrl: './guided-explore.component.scss',
})
export class GuidedExploreComponent {
  private readonly auth = inject(AuthService);
  private readonly kundlis = inject(KundliStore);

  protected readonly profileSwitcherOpen = signal(false);
  protected readonly profile = computed(() => {
    const active = this.kundlis.active();
    const name = active?.name || this.auth.email().split('@')[0] || 'Lakshmi';
    return {
      initial: name.trim().charAt(0).toUpperCase() || 'L',
      name,
    };
  });

  protected readonly cards: ExploreCard[] = [
    {
      title: 'What to Do',
      body: 'Small practices, remedies, and timing cues for how to move through the day.',
      route: ['/m', 'explore', 'what-to-do'],
      icon: 'remedy-rite',
      tone: 'gold',
    },
    {
      title: 'Your Chart',
      body: 'See the chart behind your guidance, kept simple enough to understand.',
      route: ['/m', 'chart'],
      icon: 'nav-chart',
      tone: 'good',
    },
    {
      title: 'Muhurthas',
      body: 'Pick better windows for travel, contracts, purchases, and important starts.',
      route: ['/m', 'muhurta'],
      icon: 'figma-yantra-calendar',
      tone: 'gold',
    },
    {
      title: 'Life Chapters',
      body: 'Understand the season you are in and the lessons it is asking of you.',
      route: ['/m', 'explore', 'life-chapters'],
      icon: 'nav-clock',
      tone: 'accent',
    },
  ];

  constructor() {
    if (!this.kundlis.loaded()) void this.kundlis.load().catch(() => undefined);
  }
}
