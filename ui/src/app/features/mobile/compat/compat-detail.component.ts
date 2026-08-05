import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { CompatibilityPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';

/**
 * Full Compatibility Detail (Figma 215:805) — the eight-Koota breakdown,
 * cancellation reasoning, and Manglik/Gandanta safety checks that the
 * summary screen (30c, `compat-results`) only shows a slice of.
 *
 * Every figure here already exists in `gun_milan()`'s response; this screen
 * just stops summarizing it. "Compare D1/D9" is a real, not-yet-built
 * feature and stays disabled rather than faked. "Gen AI Narrative" reuses
 * Ask — the only place in the app that generates AI narrative from grounded
 * data — instead of a second, parallel generation path.
 */
@Component({
  selector: 'as-compat-detail',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './compat-detail.component.html',
  styleUrl: './compat-detail.component.scss',
})
export class CompatDetailComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly route = inject(ActivatedRoute);

  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly score = signal<CompatibilityPayload | null>(null);
  protected readonly partnerId = signal(this.route.snapshot.queryParamMap.get('partner'));
  protected readonly partner = computed(() => this.kundlis.kundlis().find((profile) => profile.id === this.partnerId()) ?? null);
  protected readonly activeName = computed(() => this.kundlis.active()?.name ?? 'You');
  protected readonly partnerName = computed(() => this.partner()?.name ?? 'Selected person');

  /** A row reads as "cancelled" when the engine's own note says so — no new detection, just surfacing it. */
  protected readonly cancellations = computed(() =>
    (this.score()?.rows ?? []).filter((row) => /cancel/i.test(row.note)),
  );

  protected readonly askNarrativeQuery = computed(
    () => `Explain the Gun Milan compatibility between ${this.activeName()} and ${this.partnerName()}`,
  );
  protected readonly strongestRows = computed(() =>
    [...(this.score()?.rows ?? [])].sort((a, b) => b.points / Math.max(b.max, 1) - a.points / Math.max(a.max, 1)).slice(0, 2),
  );
  protected readonly cautionRows = computed(() =>
    [...(this.score()?.rows ?? [])].filter((row) => row.points < row.max).sort((a, b) => a.points / Math.max(a.max, 1) - b.points / Math.max(b.max, 1)).slice(0, 2),
  );

  constructor() {
    void this.load();
  }

  protected reload(): void {
    void this.load();
  }

  protected rowStatus(row: { verified?: boolean; points: number; max: number }): 'full' | 'caution' | 'partial' {
    if (row.verified === false) return 'partial';
    if (row.points < row.max) return 'caution';
    return 'full';
  }

  protected scoreMeaning(score: CompatibilityPayload): string {
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
      this.score.set(await this.vedic.compatibility(activeId, partnerId));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
