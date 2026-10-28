import { ChangeDetectionStrategy, Component, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { LifeStory, LifeStoryArea, VedicAll } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { BirthDetailsCardComponent } from '../chart/birth-details-card.component';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackBarComponent } from '../shared/back-bar.component';

/**
 * Your Story, as the server writes it (GET /vedic/{id}/story).
 *
 * Until 2026-10-28 this screen wrote the story itself: four element labels for
 * the headline and one of two or three fixed paragraphs per card, picked from
 * just two planets' houses, with Career always "Blessed" and Health always
 * "Watch". Now the story agent reads the whole chart through the classical
 * rules it meets, and the badges come from each house lord's real strength.
 * When the agent can't write, the server sends the same shape built from this
 * chart's own placements, so the screen has one path.
 */
@Component({
  selector: 'as-guided-story',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackBarComponent, GenericErrorComponent, RouterLink, BirthDetailsCardComponent],
  templateUrl: './guided-story.component.html',
  styleUrl: './guided-story.component.scss',
})
export class GuidedStoryComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);

  protected readonly chart = signal<VedicAll | null>(null);
  protected readonly story = signal<LifeStory | null>(null);
  protected readonly loading = signal(true);
  protected readonly writing = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly noProfile = signal(false);

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  protected badge(area: LifeStoryArea): string | null {
    return area.tone === 'strong' ? 'Strong' : area.tone === 'gentle' ? 'Go gently' : null;
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    this.story.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      this.noProfile.set(!activeId);
      if (!activeId) {
        this.chart.set(null);
        return;
      }
      // The first open writes the story, which can take a while; the birth
      // details show as soon as the chart is in.
      const story = this.vedic.story(activeId);
      story.catch(() => undefined); // awaited below; this only keeps an early failure from going unhandled
      this.chart.set(this.vedic.cachedAll(activeId) ?? await this.vedic.all(activeId));
      this.loading.set(false);
      this.writing.set(true);
      const payload = await story;
      if (this.kundlis.activeId() !== activeId) return;
      this.story.set(payload.story);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
      this.writing.set(false);
    }
  }
}
