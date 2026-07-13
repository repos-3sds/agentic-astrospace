import { Component, computed, effect, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';
import { ButtonModule } from 'primeng/button';
import { SelectButton } from 'primeng/selectbutton';
import { Skeleton } from 'primeng/skeleton';
import { Tag } from 'primeng/tag';

import { KundliStore } from '../../../core/kundli.store';
import { PredictionClaim, PredictionClaimStatus, Reading } from '../../../core/models';
import { READING_PERIODS, ReadingPeriod, ReadingService } from '../../../core/reading.service';
import { MarkdownPipe } from '../../../shared/markdown.pipe';
import { SectionCardComponent } from '../../../shared/section-card/section-card.component';

const VALIDATION_OPTIONS = [
  { label: 'Accurate', value: 5, className: 'accurate' },
  { label: 'Partly', value: 3, className: 'partly' },
  { label: 'Missed', value: 1, className: 'missed' },
  { label: 'N/A', value: 2, className: 'na' },
];

const CLAIM_STATUS_OPTIONS: { label: string; value: PredictionClaimStatus; className: string }[] = [
  { label: 'Accurate', value: 'accurate', className: 'accurate' },
  { label: 'Partly', value: 'partly', className: 'partly' },
  { label: 'Missed', value: 'missed', className: 'missed' },
  { label: 'N/A', value: 'not_applicable', className: 'na' },
];

@Component({
  selector: 'app-readings-tab',
  imports: [
    FormsModule,
    DecimalPipe,
    LucideAngularModule,
    ButtonModule,
    SelectButton,
    Skeleton,
    Tag,
    MarkdownPipe,
    SectionCardComponent,
  ],
  templateUrl: './readings-tab.component.html',
  styleUrl: './readings-tab.component.scss',
})
export class ReadingsTabComponent {
  private store = inject(KundliStore);
  private readingSvc = inject(ReadingService);

  protected readonly periods = READING_PERIODS.map((p) => ({
    label: p.charAt(0).toUpperCase() + p.slice(1),
    value: p,
  }));

  protected period: ReadingPeriod = 'daily';

  protected readonly reading = signal<Reading | null>(null);
  protected readonly history = signal<Reading[]>([]);
  protected readonly claims = signal<PredictionClaim[]>([]);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = signal(false);
  protected readonly savingFeedback = signal(false);
  protected readonly ratingDraft = signal<number | null>(null);
  protected feedbackDraft = '';
  protected claimFeedbackDrafts: Record<string, string> = {};
  protected readonly validationOptions = VALIDATION_OPTIONS;
  protected readonly claimStatusOptions = CLAIM_STATUS_OPTIONS;

  protected readonly selectedId = computed(() => this.reading()?.id ?? null);
  protected readonly selectedClaims = computed(() => {
    const readingId = this.selectedId();
    return this.claims().filter((claim) => claim.reading_id === readingId);
  });
  protected readonly validationStats = computed(() => {
    const claimRows = this.claims();
    if (claimRows.length) {
      const applicable = claimRows.filter((claim) => claim.status !== 'pending' && claim.status !== 'not_applicable');
      const score = applicable.reduce((sum, claim) => {
        if (claim.status === 'accurate') return sum + 1;
        if (claim.status === 'partly') return sum + 0.5;
        return sum;
      }, 0);
      return {
        reviewed: claimRows.filter((claim) => claim.status !== 'pending').length,
        applicable: applicable.length,
        percent: applicable.length ? Math.round((score / applicable.length) * 100) : null,
      };
    }
    const reviewed = this.history().filter((item) => item.user_rating && item.user_rating !== 2);
    const total = reviewed.length;
    const score = reviewed.reduce((sum, item) => {
      if (item.user_rating === 5) return sum + 1;
      if (item.user_rating === 4) return sum + 0.8;
      if (item.user_rating === 3) return sum + 0.5;
      return sum;
    }, 0);
    return {
      reviewed: this.history().filter((item) => !!item.user_rating).length,
      applicable: total,
      percent: total ? Math.round((score / total) * 100) : null,
    };
  });

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      if (id) this.loadHistory(true);
    });
  }

  protected onPeriodChange(period: ReadingPeriod): void {
    this.period = period;
    this.loadHistory(true);
  }

  protected async loadHistory(generateIfEmpty = false): Promise<void> {
    const id = this.store.activeId();
    if (!id) return;
    this.loading.set(true);
    this.error.set(null);
    this.reading.set(null);
    try {
      const readings = await this.readingSvc.list(id, this.period);
      this.history.set(readings);
      await this.loadClaims();
      if (readings.length) {
        this.select(readings[0]);
      } else if (generateIfEmpty) {
        await this.generate(false);
      }
    } catch (e) {
      this.error.set((e as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected async generate(forceRefresh: boolean): Promise<void> {
    const id = this.store.activeId();
    if (!id) return;
    this.loading.set(true);
    this.error.set(null);
    try {
      const generated = await this.readingSvc.generate(id, this.period, forceRefresh);
      const rest = this.history().filter((r) => r.id !== generated.id);
      this.history.set([generated, ...rest]);
      await this.loadClaims();
      this.select(generated);
    } catch (e) {
      this.error.set((e as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected select(reading: Reading): void {
    this.reading.set(reading);
    this.ratingDraft.set(reading.user_rating ?? null);
    this.feedbackDraft = reading.user_feedback ?? '';
  }

  protected async saveFeedback(): Promise<void> {
    const id = this.store.activeId();
    const reading = this.reading();
    if (!id || !reading) return;
    this.savingFeedback.set(true);
    this.error.set(null);
    try {
      const updated = await this.readingSvc.feedback(
        id,
        reading.id,
        this.ratingDraft(),
        this.feedbackDraft.trim(),
      );
      this.reading.set(updated);
      this.history.update((items) => items.map((r) => (r.id === updated.id ? updated : r)));
    } catch (e) {
      this.error.set((e as Error).message);
    } finally {
      this.savingFeedback.set(false);
    }
  }

  protected async updateClaim(claim: PredictionClaim, status: PredictionClaimStatus): Promise<void> {
    const id = this.store.activeId();
    if (!id) return;
    this.savingFeedback.set(true);
    this.error.set(null);
    try {
      const updated = await this.readingSvc.claimFeedback(
        id,
        claim.id,
        status,
        (this.claimFeedbackDrafts[claim.id] ?? '').trim(),
      );
      this.claims.update((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      this.claimFeedbackDrafts[updated.id] = updated.user_feedback ?? '';
    } catch (e) {
      this.error.set((e as Error).message);
    } finally {
      this.savingFeedback.set(false);
    }
  }

  private async loadClaims(): Promise<void> {
    const id = this.store.activeId();
    if (!id) return;
    const claims = await this.readingSvc.claims(id);
    this.claims.set(claims);
    this.claimFeedbackDrafts = Object.fromEntries(
      claims.map((claim) => [claim.id, claim.user_feedback ?? '']),
    );
  }

  protected generatedAt(reading: Reading): string {
    return reading.generated_at ? new Date(reading.generated_at).toLocaleString() : '—';
  }

  protected readingTitle(reading: Reading): string {
    const label = reading.period_label ?? reading.generated_local_date ?? 'Unlabelled';
    return `${label} · v${reading.version ?? 1}`;
  }

  protected deviationLabel(reading: Reading): string {
    if (reading.deviation_score == null) return 'baseline';
    return `${reading.deviation_score}% ${reading.deviation_summary?.band ?? 'deviation'}`;
  }

  protected validationLabel(reading: Reading): string {
    return this.validationOption(reading.user_rating)?.label ?? 'Pending';
  }

  protected validationClass(score: number | null | undefined): string {
    return this.validationOption(score)?.className ?? 'pending';
  }

  protected claimStatusLabel(status: PredictionClaimStatus): string {
    return CLAIM_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? 'Pending';
  }

  protected claimStatusClass(status: PredictionClaimStatus): string {
    return CLAIM_STATUS_OPTIONS.find((option) => option.value === status)?.className ?? 'pending';
  }

  protected claimWindow(claim: PredictionClaim): string {
    if (!claim.target_start_date) return 'undated';
    if (!claim.target_end_date || claim.target_end_date === claim.target_start_date) {
      return claim.target_start_date;
    }
    return `${claim.target_start_date} → ${claim.target_end_date}`;
  }

  private validationOption(score: number | null | undefined): (typeof VALIDATION_OPTIONS)[number] | null {
    return VALIDATION_OPTIONS.find((option) => option.value === score) ?? null;
  }
}
