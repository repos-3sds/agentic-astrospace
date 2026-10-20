import { Component, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
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
  protected readonly appCta = computed(() => (this.auth.session() ? 'Open' : 'Begin your path'));
  protected readonly appLink = computed(() => (this.auth.session() ? '/app' : '/auth'));
  /** Set by authGuard when a signed-in account other than the owner tried to open the web app. */
  protected readonly ownerOnly = toSignal(
    inject(ActivatedRoute).queryParamMap.pipe(map((params) => params.get('owner_only') === '1')),
    { initialValue: false },
  );

  protected async switchAccount(): Promise<void> {
    await this.auth.signOut(['/auth']);
  }

  protected readonly features = [
    {
      icon: 'sparkles',
      title: 'Guidance for everyday decisions',
      body: 'Ask about career, relationships, family, travel or timing and receive grounded context for real life.',
    },
    {
      icon: 'orbit',
      title: 'Your life map, made readable',
      body: 'See your rashi, nakshatra, lagna, dashas, yogas and varga charts in a calm layout that supports understanding.',
    },
    {
      icon: 'calendar-days',
      title: 'Know the rhythm of the day',
      body: 'Panchanga, transits and personal timing come together so you can see what supports action, reflection, rest or caution.',
    },
  ];

  protected readonly workflow = [
    'Add your birth details once',
    'Understand your life map, strengths and current chapter',
    'Return for daily rhythm, practices and readings you want to revisit',
  ];
}
