import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PredictionClaim, Reading } from '../../../core/models';
import { ReadingPeriod, ReadingService } from '../../../core/reading.service';
import { MarkdownPipe } from '../../../shared/markdown.pipe';

const PERIODS: Array<{ label: string; value: ReadingPeriod }> = [
  { label: 'Today', value: 'daily' },
  { label: 'This week', value: 'weekly' },
  { label: 'This month', value: 'monthly' },
  { label: 'This year', value: 'yearly' },
];

@Component({
  selector: 'as-mobile-readings',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, MarkdownPipe],
  template: `
    <a class="mrd-back" [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mrd-body">
      <header><h1>Readings</h1><p>Generated predictions and the claims you can review later.</p></header>

      <a class="mrd-track" [routerLink]="['/m','readings','accuracy']">
        <span>↗</span>
        <span><b>{{ accuracyLabel() }}</b><small>{{ accuracySubcopy() }}</small></span>
        <img src="mobile/chevron.svg" alt="" />
      </a>

      <nav class="mrd-tabs" aria-label="Reading period">
        @for (tab of periods; track tab.value) {
          <button type="button" [class.on]="period() === tab.value" [disabled]="loading()" (click)="period.set(tab.value)">
            {{ tab.label }}
          </button>
        }
      </nav>

      @if (loading()) {
        <section class="mrd-state" aria-live="polite">
          <b>Loading readings</b>
          <p>Checking saved readings for {{ activeName() }}.</p>
        </section>
      } @else if (error()) {
        <section class="mrd-state error" role="alert">
          <b>Readings could not load</b>
          <p>{{ error() }}</p>
          <button type="button" (click)="reload()">Retry</button>
        </section>
      } @else if (!activeId()) {
        <section class="mrd-state">
          <b>No active profile</b>
          <p>Create or select a profile before loading readings.</p>
        </section>
      } @else if (!readings().length) {
        <section class="mrd-state">
          <b>No {{ periodLabel().toLowerCase() }} readings yet</b>
          <p>Generate a reading to start tracking real versions and claims for this profile.</p>
          <button type="button" [disabled]="generating()" (click)="generate()">
            {{ generating() ? 'Generating' : 'Generate reading' }}
          </button>
        </section>
      } @else if (selected(); as reading) {
        <article class="mrd-reading">
          <div>
            <b>{{ readingTitle(reading) }}</b>
            <em>v{{ reading.version ?? 1 }}</em>
          </div>
          <div class="mrd-prose" [innerHTML]="reading.content | markdown"></div>
          <hr />
          <footer>
            <small>{{ generatedLabel(reading) }}</small>
            <span>{{ ratingLabel(reading) }}</span>
          </footer>
        </article>

        <div class="mrd-actions">
          <button type="button" disabled title="Saved versions are listed below">Saved versions</button>
          <button class="ink" type="button" [disabled]="generating()" (click)="generate()">
            {{ generating() ? 'Generating' : 'Generate new' }}
          </button>
        </div>

        <a class="mrd-ask" [routerLink]="['/m','ask']" [queryParams]="{ q: askQuestion(reading) }">
          <span>Ask about this reading</span>
          <img src="mobile/chevron.svg" alt="" />
        </a>

        <section class="mrd-claims">
          <div>
            <b>Claims in this reading</b>
            <small>{{ selectedClaims().length }} returned by the reading API</small>
          </div>
          @for (claim of selectedClaims(); track claim.id) {
            <article>
              <span>{{ claim.category }}</span>
              <p>{{ claim.claim_text }}</p>
              <em [attr.data-status]="claim.status">{{ claimStatusLabel(claim.status) }}</em>
            </article>
          } @empty {
            <p>No individual claims were returned for this reading.</p>
          }
        </section>

        <p class="mrd-title">SAVED VERSIONS</p>
        @for (item of readings(); track item.id) {
          <button class="mrd-earlier" type="button" [class.active]="selectedId() === item.id" (click)="select(item.id)">
            <span><b>{{ readingTitle(item) }}</b><small>{{ generatedLabel(item) }}</small></span>
            <em>{{ ratingLabel(item) }}</em>
          </button>
        }
      }
    </main>
  `,
  styleUrl: './readings.component.scss',
})
export class ReadingsComponent {
  private readonly store = inject(KundliStore);
  private readonly readingsApi = inject(ReadingService);
  private requestId = 0;

  protected readonly periods = PERIODS;
  protected readonly period = signal<ReadingPeriod>('weekly');
  protected readonly readings = signal<Reading[]>([]);
  protected readonly claims = signal<PredictionClaim[]>([]);
  protected readonly selectedId = signal<string | null>(null);
  protected readonly loading = signal(false);
  protected readonly generating = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly activeId = computed(() => this.store.activeId());
  protected readonly activeName = computed(() => this.store.active()?.name ?? 'this profile');
  protected readonly selected = computed(
    () => this.readings().find((reading) => reading.id === this.selectedId()) ?? this.readings()[0] ?? null,
  );
  protected readonly selectedClaims = computed(() => {
    const readingId = this.selected()?.id;
    return readingId ? this.claims().filter((claim) => claim.reading_id === readingId) : [];
  });
  protected readonly reviewedClaims = computed(() =>
    this.claims().filter((claim) => claim.status !== 'pending'),
  );
  protected readonly heldClaims = computed(() =>
    this.reviewedClaims().filter((claim) => claim.status === 'accurate' || claim.status === 'partly'),
  );

  constructor() {
    effect(() => {
      const id = this.activeId();
      const period = this.period();
      void this.load(id, period);
    });
  }

  protected reload(): void {
    void this.load(this.activeId(), this.period());
  }

  protected select(id: string): void {
    this.selectedId.set(id);
  }

  protected async generate(): Promise<void> {
    const id = this.activeId();
    if (!id) return;
    const request = ++this.requestId;
    this.generating.set(true);
    this.error.set(null);
    try {
      const generated = await this.readingsApi.generate(id, this.period(), true);
      if (request !== this.requestId || this.activeId() !== id) return;
      this.readings.update((items) => [generated, ...items.filter((item) => item.id !== generated.id)]);
      this.selectedId.set(generated.id);
      await this.loadClaims(id, request);
    } catch (error) {
      if (request === this.requestId) this.error.set((error as Error).message);
    } finally {
      if (request === this.requestId) this.generating.set(false);
    }
  }

  protected periodLabel(): string {
    return this.periods.find((period) => period.value === this.period())?.label ?? 'selected';
  }

  protected accuracyLabel(): string {
    const reviewed = this.reviewedClaims().length;
    if (!reviewed) return 'No reviewed claims yet';
    return `${this.heldClaims().length} of ${reviewed} held or partly held`;
  }

  protected accuracySubcopy(): string {
    const total = this.claims().length;
    if (!total) return 'No prediction claims returned yet';
    return `${total} total claims for ${this.activeName()}`;
  }

  protected readingTitle(reading: Reading): string {
    return reading.period_label ?? reading.generated_local_date ?? reading.reading_type;
  }

  protected generatedLabel(reading: Reading): string {
    if (!reading.generated_at) return 'Generated date unavailable';
    return `Generated ${new Date(reading.generated_at).toLocaleDateString()}`;
  }

  protected ratingLabel(reading: Reading): string {
    if (reading.user_rating == null) return 'Pending review';
    if (reading.user_rating === 5) return 'Accurate';
    if (reading.user_rating === 3) return 'Partly';
    if (reading.user_rating === 2) return 'N/A';
    if (reading.user_rating === 1) return 'Missed';
    return `${reading.user_rating}/5`;
  }

  protected askQuestion(reading: Reading): string {
    return `Explain this ${this.readingTitle(reading)} reading in simple terms and what I should do next`;
  }

  protected claimStatusLabel(status: PredictionClaim['status']): string {
    if (status === 'not_applicable') return 'N/A';
    return status.replace('_', ' ');
  }

  private async load(id: string | null, period: ReadingPeriod): Promise<void> {
    const request = ++this.requestId;
    this.error.set(null);
    this.selectedId.set(null);
    this.readings.set([]);
    this.claims.set([]);
    if (!id) return;
    this.loading.set(true);
    try {
      const readings = await this.readingsApi.list(id, period);
      if (request !== this.requestId || this.activeId() !== id || this.period() !== period) return;
      this.readings.set(readings);
      this.selectedId.set(readings[0]?.id ?? null);
      await this.loadClaims(id, request);
    } catch (error) {
      if (request === this.requestId) this.error.set((error as Error).message);
    } finally {
      if (request === this.requestId) this.loading.set(false);
    }
  }

  private async loadClaims(id: string, request: number): Promise<void> {
    const claims = await this.readingsApi.claims(id);
    if (request !== this.requestId || this.activeId() !== id) return;
    this.claims.set(claims);
  }
}
