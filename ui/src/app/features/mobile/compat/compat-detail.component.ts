import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { CompatibilityPayload } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';

/**
 * Full Compatibility Detail (Figma 215:805) — the eight-Koota breakdown,
 * cancellation reasoning, and Manglik/Gandanta safety checks that the
 * summary screen (30c, `compat-results`) only shows a slice of.
 *
 * Every figure here already exists in `gun_milan()`'s response; this screen
 * just stops summarizing it. A D1/D9 comparison is not built yet, so no
 * button promises one. "Ask about this match" reuses Ask — the only place in
 * the app that generates AI narrative from grounded data — instead of a
 * second, parallel generation path.
 *
 * A married tester asked what the two of them can actually do. The screen now
 * leads with the server's plain couple guidance (what already works, where a
 * little care helps, something for each of you) and keeps every koota term
 * under one "Why this?" fold, open by default only in Practitioner mode.
 */
@Component({
  selector: 'as-compat-detail',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, GenericErrorComponent, RouterLink],
  templateUrl: './compat-detail.component.html',
  styleUrl: './compat-detail.component.scss',
})
export class CompatDetailComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly route = inject(ActivatedRoute);
  private readonly preferences = inject(PreferencesService);

  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly score = signal<CompatibilityPayload | null>(null);
  protected readonly partnerId = signal(this.route.snapshot.queryParamMap.get('partner'));
  protected readonly partner = computed(() => this.kundlis.kundlis().find((profile) => profile.id === this.partnerId()) ?? null);
  protected readonly activeName = computed(() => this.kundlis.active()?.name ?? 'You');
  protected readonly partnerName = computed(() => this.partner()?.name ?? 'Selected person');
  protected readonly practitioner = computed(() => this.preferences.experienceMode() === 'practitioner');
  /** The reader's own answer wins; a saved spouse starts on "Already married". */
  private readonly marriedChoice = signal<boolean | null>(readMarried(this.partnerId()));
  protected readonly married = computed(() => this.marriedChoice() ?? this.partner()?.relation === 'spouse');
  protected readonly guidance = computed(() => this.score()?.guidance ?? null);

  /** A row reads as "cancelled" when the engine's own note says so — no new detection, just surfacing it. */
  protected readonly cancellations = computed(() =>
    (this.score()?.rows ?? []).filter((row) => /cancel/i.test(row.note)),
  );

  protected readonly askNarrativeQuery = computed(() => this.married()
    ? `${this.activeName()} and ${this.partnerName()} are already married. From our match, what can each of us do, and what can we do together, to make things better?`
    : `Explain the Gun Milan compatibility between ${this.activeName()} and ${this.partnerName()}`);
  protected readonly strongestRows = computed(() =>
    [...(this.score()?.rows ?? [])].sort((a, b) => b.points / Math.max(b.max, 1) - a.points / Math.max(a.max, 1)).slice(0, 2),
  );
  protected readonly cautionRows = computed(() =>
    [...(this.score()?.rows ?? [])].filter((row) => row.points < row.max).sort((a, b) => a.points / Math.max(a.max, 1) - b.points / Math.max(b.max, 1)).slice(0, 2),
  );
  protected readonly dashakootaRows = computed(() => this.score()?.dashakoota_extension?.rows ?? []);
  protected readonly dashakootaSummary = computed(() => {
    const extension = this.score()?.dashakoota_extension;
    if (!extension) return 'The South Indian checks (Rajju, Vedha, Stree Deergha) are not available for this pair.';
    const flagged = extension.hard_blockers ?? [];
    const result = flagged.length
      ? `${flagged.join(' and ')} ${flagged.length > 1 ? 'are' : 'is'} flagged. South Indian practice looks more carefully when that happens; it is a caution, not a verdict.`
      : extension.total >= extension.max
        ? 'All three are clear.'
        : 'Neither Rajju nor Vedha is flagged.';
    return `${extension.total} of ${extension.max} on the three South Indian checks, kept apart from the 36 points. ${result}`;
  });

  constructor() {
    void this.load();
  }

  protected reload(): void {
    void this.load();
  }

  protected setMarried(married: boolean): void {
    this.marriedChoice.set(married);
    writeMarried(this.partnerId(), married);
  }

  /**
   * By score alone. Whether traditions agree on a row (`verified`) is the
   * engine's bookkeeping, covered by the observance note; tagging a 7 of 7 as
   * "partial" for it read as a half score.
   */
  protected rowStatus(row: { points: number; max: number }): 'full' | 'partial' | 'low' {
    if (row.points >= row.max) return 'full';
    return row.points > 0 ? 'partial' : 'low';
  }

  protected rowStatusLabel(row: { points: number; max: number }): string {
    return { full: '✓', partial: 'PARTIAL', low: 'LOW' }[this.rowStatus(row)];
  }

  protected manglikBadge(score: CompatibilityPayload): string {
    const manglik = score.safety_checks.manglik;
    if (!manglik.match) return 'Review';
    return manglik.person1_active && manglik.person2_active ? 'Balanced' : 'Clear';
  }

  protected scoreMeaning(score: CompatibilityPayload): string {
    if (this.married()) return 'You are already married, so this score is not a pass or a fail. It only shows where a little care helps most.';
    const ratio = score.total / Math.max(score.max, 1);
    if (ratio >= 0.75) return 'The match has strong baseline agreement. Use the details below to protect the weaker areas instead of treating the score as a guarantee.';
    if (ratio >= 0.5) return 'The match has workable support, but it needs conscious effort in the caution areas below.';
    return 'The match asks for careful review. Do not rely on the total alone; the weaker kootas and safety checks matter more here.';
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    this.score.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      const partnerId = this.partnerId();
      if (!activeId || !partnerId) return;
      const partnerIsGroom = this.route.snapshot.queryParamMap.get('groom') === 'partner';
      this.score.set(partnerIsGroom
        ? await this.vedic.compatibility(partnerId, activeId)
        : await this.vedic.compatibility(activeId, partnerId));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}

const MARRIED_KEY = 'as.compat.married.';

function readMarried(partnerId: string | null): boolean | null {
  if (!partnerId) return null;
  try {
    const value = localStorage.getItem(MARRIED_KEY + partnerId);
    return value === null ? null : value === '1';
  } catch {
    return null;
  }
}

function writeMarried(partnerId: string | null, married: boolean): void {
  if (!partnerId) return;
  try {
    localStorage.setItem(MARRIED_KEY + partnerId, married ? '1' : '0');
  } catch {
    // Private mode or blocked storage: the choice lasts for this visit only.
  }
}
