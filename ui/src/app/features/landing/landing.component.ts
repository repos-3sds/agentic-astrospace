import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';

import { AuthService } from '../../core/auth.service';
import { ThemeService } from '../../core/theme.service';

@Component({
  selector: 'app-landing',
  imports: [RouterLink, LucideAngularModule],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
})
export class LandingComponent {
  protected readonly auth = inject(AuthService);
  protected readonly theme = inject(ThemeService);
  protected readonly appCta = computed(() => (this.auth.session() ? 'Open your chart' : 'Explore your chart'));
  protected readonly appLink = computed(() => (this.auth.session() ? '/app' : '/auth'));

  protected readonly features = [
    {
      icon: 'sparkles',
      title: 'Guidance for everyday decisions',
      body: 'Ask about career, relationships, family, travel or timing and get a reading that connects your chart to real life.',
    },
    {
      icon: 'orbit',
      title: 'Your kundli, made readable',
      body: 'See your rashi, nakshatra, lagna, dashas, yogas and varga charts in a calm layout that normal people can actually follow.',
    },
    {
      icon: 'calendar-days',
      title: 'Know the mood of the day',
      body: 'Panchanga, transits and personal timing come together so you can see what supports action, reflection, rest or caution.',
    },
  ];

  protected readonly workflow = [
    'Add your birth details once',
    'Understand your chart, strengths and current dasha',
    'Check daily timing and save readings you want to revisit',
  ];
}
