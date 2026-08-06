import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { KundliStore } from '../../../core/kundli.store';
import {
  RemedyRecommendationGroup,
  RemedyRecommendationPractice,
  RemedyRecommendationsPayload,
  VedicService,
} from '../../../core/vedic.service';
import { PreferencesService } from '../../../core/preferences.service';

/** What kind of thing in the chart a remedy answers to. */
export type RemedyTone = 'warn' | 'bad' | 'good';

/**
 * Remedies — "What to do" (Figma node 29:55).
 *
 * Titled the way the design titles it. "Remedies" implies something is wrong
 * and this will fix it; "What to do" is the same content without the premise.
 *
 * Two product constraints are load-bearing here and are enforced in the
 * template rather than the data:
 *
 * - Remedies are **traditional practice, never "pay to remove"**. Every card
 *   carries "Traditional practice · not a guarantee" above its action, printed
 *   by the template so no card object can omit it and no future card can be
 *   added without it.
 * - A dosha is **a flag, not a verdict** — never suppressed, never escalated.
 *   The Manglik card says the influence is mild, common, and has a traditional
 *   cancellation. That wording is the constraint, not filler: dropping "common"
 *   escalates it, and dropping the flag entirely suppresses it.
 *
 * The lede states the limit once for the whole screen, and the per-card line
 * repeats it at the point of action, because that is where someone decides.
 */
@Component({
  selector: 'as-remedies',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './remedies.component.html',
  styleUrl: './remedies.component.scss',
})
export class RemediesComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly preferences = inject(PreferencesService);
  protected readonly recommendations = signal<RemedyRecommendationsPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly groups = computed(() => this.recommendations()?.groups ?? []);
  protected readonly note = computed(() => this.recommendations()?.note ?? null);
  protected readonly disclaimer = computed(() => this.recommendations()?.disclaimer ?? 'Traditional practice, not a guarantee.');

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  protected backRoute(): string[] {
    const mode = this.preferences.experienceMode();
    if (mode === 'guided') return ['/m', 'explore'];
    if (mode === 'balanced') return ['/m', 'chart'];
    return ['/m', 'chart'];
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.recommendations.set(null);
        return;
      }
      this.recommendations.set(await this.vedic.remedies(activeId, {
        includeCostly: false,
        includeManglik: false,
      }));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected tag(group: RemedyRecommendationGroup): string {
    const trigger = group.trigger;
    if (trigger.kind === 'dasha' && trigger.planet) return `${trigger.planet.toUpperCase()} ${trigger.level?.toUpperCase() ?? 'DASHA'}`;
    if (trigger.kind === 'dignity' && trigger.planet) return `${trigger.planet.toUpperCase()} DIGNITY`;
    if (trigger.kind === 'combustion' && trigger.planet) return `${trigger.planet.toUpperCase()} COMBUST`;
    if (trigger.kind === 'dosha' && trigger.dosha) return `${trigger.dosha.toUpperCase()} FLAG`;
    return trigger.kind.toUpperCase();
  }

  protected tone(group: RemedyRecommendationGroup): RemedyTone {
    if (group.trigger.kind === 'dosha') return 'bad';
    if (group.trigger.kind === 'dasha') return 'warn';
    return 'good';
  }

  protected icon(practice: RemedyRecommendationPractice): 'chant' | 'offer' | 'wear' | 'rite' {
    if (practice.type === 'mantra') return 'chant';
    if (practice.type === 'donation') return 'offer';
    if (practice.type === 'colour' || practice.type === 'gem') return 'wear';
    return 'rite';
  }

  protected practiceRoute(group: RemedyRecommendationGroup, practice: RemedyRecommendationPractice): string[] {
    return ['/m', 'remedies', 'mantra'];
  }

  protected practiceParams(group: RemedyRecommendationGroup, practice: RemedyRecommendationPractice): Record<string, string> {
    return {
      recommendation: group.recommendation_id,
      practice: practice.practice_slug,
    };
  }

  protected practiceCta(practice: RemedyRecommendationPractice): string {
    if (practice.type === 'mantra') return 'Start 108 practice';
    if (practice.type === 'deity') return 'Track prayer';
    return 'Open practice';
  }

  protected isTrackable(practice: RemedyRecommendationPractice): boolean {
    return !practice.optional_cost && (practice.type === 'mantra' || practice.type === 'deity');
  }

  protected practiceNote(practice: RemedyRecommendationPractice): string {
    if (practice.type === 'donation') return 'Offering';
    if (practice.type === 'colour' || practice.type === 'gem') return 'Wear/use';
    return practice.optional_cost ? 'Optional' : 'No tracking';
  }

  protected groupReason(group: RemedyRecommendationGroup): string {
    return this.humanizeDates(group.reason_practitioner);
  }

  protected sourceLabel(group: RemedyRecommendationGroup): string {
    const status = group.source_status.replaceAll('_', ' ');
    return `${status} · ${group.tradition_source}`;
  }

  protected practiceMeta(practice: RemedyRecommendationPractice): string {
    const parts = [
      this.practiceTypeLabel(practice),
      practice.cadence,
      practice.preferred_day,
      practice.target_count ? `${practice.target_count} count` : null,
    ].filter(Boolean);
    return parts.join(' · ');
  }

  private practiceTypeLabel(practice: RemedyRecommendationPractice): string {
    if (practice.type === 'mantra') return 'Mantra';
    if (practice.type === 'donation') return 'Offering';
    if (practice.type === 'colour') return 'Colour';
    if (practice.type === 'deity') return 'Prayer';
    if (practice.type === 'gem') return 'Gemstone';
    return 'Practice';
  }

  private humanizeDates(value: string): string {
    return value.replace(
      /\b(\d{4}-\d{2}-\d{2})(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?\b/g,
      (match, datePart: string) => this.dateLabel(datePart) || match,
    );
  }

  private dateLabel(value: string): string {
    const date = new Date(`${value}T12:00:00`);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }
}
