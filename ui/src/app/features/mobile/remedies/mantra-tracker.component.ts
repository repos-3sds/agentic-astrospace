import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { KundliStore } from '../../../core/kundli.store';
import {
  RemedyRecommendationGroup,
  RemedyRecommendationPractice,
  VedicService,
} from '../../../core/vedic.service';
import { HapticsService } from '../../../core/haptics.service';

/**
 * Remedy detail — mantra tracker (Figma node 29:109).
 *
 * The count ring is data, not decoration: it redraws on every tap, so — like
 * the day gauge (13:20) — it is a stroked circle rather than the pasted export.
 * The geometry is lifted from the export so it lines up exactly:
 *
 *   outer radius 110, band 15.4 wide  ->  stroke-width 15.4, centre r 102.3
 *   track #e6dccd (--m-border), arc #b13f2e (--m-accent)
 *
 * The two exported ellipses are the only assets deliberately not used verbatim.
 *
 * On the counting itself: the target is a traditional count (108), and the
 * screen says "traditional practice" in the eyebrow and again above the fold.
 * The streak is there to help someone keep a practice they chose, which is why
 * nothing here warns about breaking it — a lapsed streak is not a consequence,
 * and dressing it as one would turn a practice into a debt.
 */
@Component({
  selector: 'as-mantra-tracker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './mantra-tracker.component.html',
  styleUrl: './mantra-tracker.component.scss',
})
export class MantraTrackerComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly haptics = inject(HapticsService);
  private readonly params = toSignal(this.route.queryParamMap, { requireSync: true });

  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly group = signal<RemedyRecommendationGroup | null>(null);
  protected readonly practice = signal<RemedyRecommendationPractice | null>(null);
  protected readonly count = signal(0);
  protected readonly completedDates = signal<string[]>([]);
  protected readonly mode = signal<'manual' | 'auto'>('manual');

  protected readonly eyebrow = computed(() => {
    const trigger = this.group()?.trigger;
    if (!trigger) return 'TRADITIONAL PRACTICE';
    if (trigger.kind === 'dasha') return `${trigger.planet ?? 'Planet'} ${trigger.level ?? 'dasha'} · traditional practice`.toUpperCase();
    return `${trigger.kind} · traditional practice`.toUpperCase();
  });
  protected readonly practiceTitle = computed(() => this.practice()?.title ?? 'Selected practice');
  protected readonly practiceTextLabel = computed(() => this.practice()?.type === 'mantra' ? 'MANTRA' : 'PRACTICE TEXT');
  protected readonly literalPracticeText = computed(() => {
    const practice = this.practice();
    if (!practice) return '';
    if (practice.type !== 'mantra') return this.devotionalFallback(practice);
    const audio = this.practice()?.audio;
    return audio?.text || audio?.transliteration || practice.title;
  });
  protected readonly target = computed(() => this.practice()?.target_count ?? (this.practice()?.type === 'deity' ? 1 : 108));
  protected readonly audioPending = computed(() => this.practice()?.audio?.source_status === 'pending_assets' || !this.practice()?.audio?.audio_url);

  protected readonly streakLabel = computed(() => {
    const days = this.completedDates().length;
    return days ? `${days}-day practice history` : 'Start this practice today';
  });

  // Ring geometry, from the 220px export.
  protected readonly SIZE = 220;
  protected readonly C = 110;
  protected readonly R = 102.3;
  protected readonly STROKE = 15.4;
  protected readonly CIRCUMFERENCE = 2 * Math.PI * 102.3;

  protected readonly dashOffset = computed(() => {
    const target = this.target();
    const fraction = target > 0 ? this.count() / target : 0;
    return this.CIRCUMFERENCE * (1 - Math.min(1, Math.max(0, fraction)));
  });

  constructor() {
    void this.load();
  }

  /** Counts up to the target and stops. Past 108 the count means nothing. */
  protected tap(): void {
    this.haptics.tap();
    this.count.update((n) => {
      const next = Math.min(this.target(), n + 1);
      if (next >= this.target()) {
        this.completeToday();
      } else {
        this.persist(next, this.completedDates());
      }
      return next;
    });
  }

  protected readonly done = computed(() => this.count() >= this.target());

  protected resetToday(): void {
    this.count.set(0);
    this.persist(0, this.completedDates());
  }

  protected completeToday(): void {
    const today = this.todayKey();
    const dates = this.completedDates().includes(today)
      ? this.completedDates()
      : [...this.completedDates(), today];
    this.completedDates.set(dates);
    this.persist(this.target(), dates);
    this.haptics.success();
  }

  protected audioNote(): string {
    return this.practice()?.audio?.note ?? 'Recorded audio is not available yet. Manual counting is ready.';
  }

  protected practiceContext(): string {
    const practice = this.practice();
    const group = this.group();
    const pieces = [
      practice?.type === 'mantra' ? '108-count mantra' : 'Prayer practice',
      practice?.preferred_day,
      practice?.planet,
      group?.reason_short,
    ].filter(Boolean);
    return pieces.join(' · ');
  }

  protected reminderLabel(): string {
    const practice = this.practice();
    if (!practice) return 'Set practice reminder';
    const day = practice.preferred_day || 'practice';
    return practice.type === 'mantra' ? `Set ${day} mantra reminder` : `Set ${day} prayer reminder`;
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (!activeId) throw new Error('Select a profile before opening a practice.');
      const recommendationId = this.params().get('recommendation');
      const practiceSlug = this.params().get('practice');
      if (!recommendationId || !practiceSlug) throw new Error('Practice selection is missing.');
      const payload = await this.vedic.remedies(activeId, {
        includeCostly: false,
        includeManglik: false,
      });
      const group = payload.groups.find((row) => row.recommendation_id === recommendationId) ?? null;
      const practice = group?.practices.find((row) => row.practice_slug === practiceSlug) ?? null;
      if (!group || !practice) throw new Error('This practice is no longer active for the selected profile.');
      this.group.set(group);
      this.practice.set(practice);
      this.restore(activeId, recommendationId, practiceSlug);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private storageKey(): string | null {
    const activeId = this.kundlis.activeId();
    const recommendationId = this.params().get('recommendation');
    const practiceSlug = this.params().get('practice');
    if (!activeId || !recommendationId || !practiceSlug) return null;
    return `siddha.remedyPractice:v1:${activeId}:${recommendationId}:${practiceSlug}`;
  }

  private restore(activeId: string, recommendationId: string, practiceSlug: string): void {
    const key = `siddha.remedyPractice:v1:${activeId}:${recommendationId}:${practiceSlug}`;
    try {
      const stored = JSON.parse(localStorage.getItem(key) || 'null') as { count?: number; completedDates?: string[] } | null;
      this.count.set(Math.min(this.target(), Math.max(0, stored?.count ?? 0)));
      this.completedDates.set(Array.isArray(stored?.completedDates) ? stored.completedDates : []);
    } catch {
      this.count.set(0);
      this.completedDates.set([]);
    }
  }

  private persist(count: number, completedDates: string[]): void {
    const key = this.storageKey();
    if (!key) return;
    localStorage.setItem(key, JSON.stringify({
      count,
      completedDates,
      updatedAt: new Date().toISOString(),
    }));
  }

  private todayKey(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private devotionalFallback(practice: RemedyRecommendationPractice): string {
    if (practice.type !== 'deity') return practice.instructions;
    const deity = practice.title.replace(/^Prayer to\s+/i, '').trim();
    return deity ? `Offer a simple prayer to ${deity}. Sit quietly, state your intention, and close with gratitude.` : practice.instructions;
  }
}
