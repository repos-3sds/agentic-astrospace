import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ManglikCancellationSheetComponent } from '../chart/manglik-cancellation-sheet.component';
import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload, YogasDoshasPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { PreferencesService } from '../../../core/preferences.service';

/** What kind of thing in the chart a remedy answers to. */
export type RemedyTone = 'warn' | 'bad' | 'good';

/** One practice. `icon` names the kind of act, not the planet. */
export interface RemedyPractice {
  icon: 'chant' | 'offer' | 'wear' | 'rite';
  text: string;
}

export interface RemedyCard {
  id: string;
  title: string;
  tagLabel: string;
  tone: RemedyTone;
  /** Why this is being shown at all — the chart fact behind it. */
  rationale: string;
  practices: RemedyPractice[];
  ctaLabel: string;
  /**
   * Where the action goes when it is a route. Manglik opens its shared sheet.
   */
  ctaRoute?: string[];
}

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
  imports: [RouterLink, ManglikCancellationSheetComponent],
  templateUrl: './remedies.component.html',
  styleUrl: './remedies.component.scss',
})
export class RemediesComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly preferences = inject(PreferencesService);
  readonly cancellationOpen = signal(false);
  protected readonly dashas = signal<DashaPayload | null>(null);
  protected readonly yogas = signal<YogasDoshasPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  readonly cards = computed<RemedyCard[]>(() => {
    const cards: RemedyCard[] = [];
    const activeLord = this.dashas()?.current.antardasha?.lord ?? this.dashas()?.current.mahadasha?.lord;
    if (activeLord) {
      cards.push({
        id: `dasha-${activeLord}`,
        title: `For your active ${activeLord} period`,
        tagLabel: `${activeLord.toUpperCase()} DASHA`,
        tone: 'warn',
        rationale: `${activeLord} is active in the returned dasha stack, so the practice is labelled as traditional support rather than a guaranteed fix.`,
        practices: this.planetPractices(activeLord),
        ctaLabel: 'Start local streak',
        ctaRoute: ['/m', 'remedies', 'mantra'],
      });
    }
    const manglik = this.yogas()?.doshas.manglik;
    if (manglik) {
      const exception = manglik.exceptions?.find((row) => row.applies);
      cards.push({
        id: 'manglik',
        title: manglik.active ? 'For the Manglik flag' : 'Manglik check',
        tagLabel: manglik.active ? 'MARRIAGE · FLAG' : 'NOT PRESENT',
        tone: manglik.active ? 'bad' : 'good',
        rationale: exception?.detail ?? manglik.rule,
        practices: manglik.active
          ? [
              { icon: 'rite', text: 'Discuss the flag and any returned exceptions with a qualified family practitioner.' },
              { icon: 'chant', text: 'Hanuman Chalisa on Tuesdays, if this is already part of your tradition.' },
            ]
          : [{ icon: 'offer', text: 'No Manglik-specific action is recommended by the returned calculation.' }],
        ctaLabel: 'View cancellation',
      });
    }
    return cards;
  });

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
    return this.preferences.experienceMode() === 'guided' ? ['/m', 'explore'] : ['/m', 'today'];
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.dashas.set(null);
        this.yogas.set(null);
        return;
      }
      const [dashas, yogas] = await Promise.all([
        this.vedic.dashas(activeId).catch(() => null),
        this.vedic.yogasDoshas(activeId).catch(() => null),
      ]);
      this.dashas.set(dashas);
      this.yogas.set(yogas);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private planetPractices(planet: string): RemedyPractice[] {
    const lower = planet.toLowerCase();
    if (lower === 'saturn') return [
      { icon: 'chant', text: 'Chant “Om Sham Shanaishcharaya Namah” · 108 times, Saturdays' },
      { icon: 'offer', text: 'Offer sesame oil or donate black sesame on Saturdays' },
    ];
    if (lower === 'mars') return [
      { icon: 'chant', text: 'Hanuman Chalisa on Tuesdays' },
      { icon: 'offer', text: 'Donate red lentils or support service work on Tuesdays' },
    ];
    if (lower === 'moon') return [
      { icon: 'chant', text: 'Chant “Om Som Somaya Namah” on Mondays' },
      { icon: 'offer', text: 'Offer milk or rice as a traditional Monday practice' },
    ];
    return [
      { icon: 'chant', text: `Use a traditional ${planet} mantra only if it belongs to your practice.` },
      { icon: 'offer', text: 'Choose simple service or donation over paid “removal” claims.' },
    ];
  }
}
