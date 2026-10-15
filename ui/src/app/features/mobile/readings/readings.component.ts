import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PredictionClaim, PredictionClaimStatus, Reading } from '../../../core/models';
import { ReadingPeriod, ReadingService } from '../../../core/reading.service';
import { MarkdownPipe } from '../../../shared/markdown.pipe';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { REVIEW_OPTIONS, claimIsDue, claimWindow } from './claim-review';

// Generation runs one model call over the chart, transits and dashas and
// usually takes 20-40 s. The stages are paced by elapsed time (the API does
// not stream progress) so the user sees the work moving instead of a static
// label.
const GENERATE_STAGES: Array<{ after: number; label: string }> = [
  { after: 0, label: 'Reading your chart' },
  { after: 4, label: 'Checking current dashas and transits' },
  { after: 12, label: 'Writing your reading' },
  { after: 30, label: 'Pulling out claims to track' },
];
const GENERATE_SLOW_AFTER = 50;

const PERIODS: Array<{ label: string; value: ReadingPeriod }> = [
  { label: 'Today', value: 'daily' },
  { label: 'Week', value: 'weekly' },
  { label: 'Month', value: 'monthly' },
  { label: 'Year', value: 'yearly' },
];

const PERIOD_NOUN: Record<ReadingPeriod, string> = {
  daily: 'daily',
  weekly: 'weekly',
  monthly: 'monthly',
  quarterly: 'quarterly',
  yearly: 'yearly',
};

const STAMP = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });

@Component({
  selector: 'as-mobile-readings',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, GenericErrorComponent, RouterLink, MarkdownPipe],
  template: `
    <a class="mrd-back" [asBack]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mrd-body">
      <header><h1>Readings</h1><p>What your chart points to, and a record of what actually happened.</p></header>

      <a class="mrd-track" [routerLink]="['/m','readings','accuracy']">
        <span>↗</span>
        <span><b>{{ trackLabel() }}</b><small>{{ trackSubcopy() }}</small></span>
        <img src="mobile/chevron.svg" alt="" />
      </a>

      <nav class="mrd-tabs" aria-label="Reading period">
        @for (tab of periods; track tab.value) {
          <button type="button" [class.on]="period() === tab.value" [disabled]="loading() || generating()" (click)="period.set(tab.value)">
            {{ tab.label }}
          </button>
        }
      </nav>

      @if (generateError(); as message) {
        <section class="mrd-state error" role="alert">
          <b>That reading didn’t finish</b>
          <p>{{ message }}</p>
          <button type="button" (click)="generate()">Try again</button>
        </section>
      }

      @if (loading()) {
        <section class="mrd-state" aria-live="polite">
          <b>Loading readings</b>
          <p>Checking saved readings for {{ activeName() }}.</p>
        </section>
      } @else if (generating()) {
        <section class="mrd-progress" role="status" aria-live="polite">
          <div class="mrd-progress-head">
            <span class="mrd-spinner" aria-hidden="true"></span>
            <span>
              <b>Writing your {{ periodNoun() }} reading</b>
              <small>{{ elapsed() }}s · usually 20–40 seconds</small>
            </span>
          </div>
          <div class="mrd-bar" role="progressbar" aria-label="Reading generation progress"
            aria-valuemin="0" aria-valuemax="100" [attr.aria-valuenow]="progress()">
            <i [style.width.%]="progress()"></i>
          </div>
          <ol>
            @for (stage of stages; track stage.label; let i = $index) {
              <li [class.done]="i < stageIndex()" [class.on]="i === stageIndex()">{{ stage.label }}</li>
            }
          </ol>
          @if (elapsed() >= slowAfter) {
            <p>Taking a little longer than usual. Keep this screen open; your reading is still being written.</p>
          }
        </section>
      } @else if (loadError()) {
        <as-generic-error role="alert" [message]="loadError()!" (retried)="reload()" />
      } @else if (!activeId()) {
        <section class="mrd-state">
          <b>No active profile</b>
          <p>Create or select a profile to get readings.</p>
        </section>
      } @else if (!readings().length) {
        @if (!generateError()) {
          <section class="mrd-state">
            <b>No {{ periodNoun() }} reading yet</b>
            <p>Get a {{ periodNoun() }} reading for {{ activeName() }}. Its predictions will be listed below it so you can check them as the days pass.</p>
            <button type="button" (click)="generate()">Get my {{ periodNoun() }} reading</button>
          </section>
        }
      } @else if (selected(); as reading) {
        @if (!isLatest(reading)) {
          <div class="mrd-older" role="note">
            <span>You’re looking at an earlier version.</span>
            <button type="button" (click)="select(readings()[0].id)">Back to latest</button>
          </div>
        }

        <article class="mrd-reading">
          <div>
            <b>{{ readingTitle(reading) }}</b>
            <em [class.latest]="isLatest(reading)">{{ isLatest(reading) ? 'Latest' : 'Version ' + (reading.version ?? 1) }}</em>
          </div>
          <div class="mrd-prose" [innerHTML]="reading.content | markdown"></div>
          <hr />
          <footer><small>{{ versionLine(reading) }}</small></footer>
        </article>

        <div class="mrd-actions">
          <a [routerLink]="['/m','ask']" [queryParams]="{ q: askQuestion(reading) }">Ask about this</a>
          <button class="ink" type="button" (click)="generate()">New version</button>
        </div>

        <section class="mrd-claims" aria-labelledby="mrd-claims-title">
          <div>
            <b id="mrd-claims-title">Predictions to check</b>
            @if (selectedClaims().length) {
              <small>{{ checkedCount() }} of {{ selectedClaims().length }} checked</small>
            }
          </div>
          @if (selectedClaims().length) {
            <p>As each one plays out, mark what happened. Your track record is built from these.</p>
          }
          @for (claim of selectedClaims(); track claim.id) {
            <article [class.checked]="claim.status !== 'pending'">
              <span>{{ claim.category }}@if (window(claim)) { · {{ window(claim) }}}</span>
              <p>{{ claim.claim_text }}</p>
              <div class="mrd-chips" role="group" [attr.aria-label]="'Did this happen? ' + claim.claim_text">
                @for (option of reviewOptions; track option.status) {
                  <button type="button" [attr.data-tone]="option.tone"
                    [class.on]="claim.status === option.status"
                    [attr.aria-pressed]="claim.status === option.status"
                    [disabled]="savingId() === claim.id"
                    (click)="review(claim, option.status)">{{ option.label }}</button>
                }
              </div>
            </article>
          } @empty {
            <p>This reading has no specific predictions to check.</p>
          }
          @if (reviewError(); as message) {
            <p class="mrd-review-error" role="alert">{{ message }}</p>
          }
        </section>

        @if (readings().length > 1) {
          <p class="mrd-title">EARLIER VERSIONS</p>
          @for (item of readings(); track item.id) {
            @if (item.id !== reading.id) {
              <button class="mrd-earlier" type="button" (click)="select(item.id)">
                <span>
                  <b>Version {{ item.version ?? 1 }}@if (isLatest(item)) { (latest)}</b>
                  <small>Written {{ stamp(item) }}</small>
                </span>
                <em>{{ checkedLabel(item) }}</em>
                <img src="mobile/chevron.svg" alt="" />
              </button>
            }
          }
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
  private elapsedTimer: ReturnType<typeof setInterval> | null = null;

  protected readonly periods = PERIODS;
  protected readonly stages = GENERATE_STAGES;
  protected readonly slowAfter = GENERATE_SLOW_AFTER;
  protected readonly reviewOptions = REVIEW_OPTIONS;
  protected readonly window = claimWindow;
  protected readonly period = signal<ReadingPeriod>('weekly');
  protected readonly readings = signal<Reading[]>([]);
  protected readonly claims = signal<PredictionClaim[]>([]);
  protected readonly selectedId = signal<string | null>(null);
  protected readonly loading = signal(false);
  protected readonly generating = signal(false);
  protected readonly loadError = signal<string | null>(null);
  protected readonly generateError = signal<string | null>(null);
  protected readonly reviewError = signal<string | null>(null);
  protected readonly savingId = signal<string | null>(null);
  protected readonly elapsed = signal(0);

  protected readonly stageIndex = computed(() => {
    const seconds = this.elapsed();
    let index = 0;
    GENERATE_STAGES.forEach((stage, i) => { if (seconds >= stage.after) index = i; });
    return index;
  });
  // Eases towards 95% and never claims completion until the API answers.
  protected readonly progress = computed(() => Math.round(95 * (1 - Math.exp(-this.elapsed() / 18))));

  protected readonly activeId = computed(() => this.store.activeId());
  protected readonly activeName = computed(() => this.store.active()?.name ?? 'this profile');
  protected readonly periodNoun = computed(() => PERIOD_NOUN[this.period()]);
  protected readonly selected = computed(
    () => this.readings().find((reading) => reading.id === this.selectedId()) ?? this.readings()[0] ?? null,
  );
  protected readonly selectedClaims = computed(() => {
    const readingId = this.selected()?.id;
    return readingId ? this.claims().filter((claim) => claim.reading_id === readingId) : [];
  });
  protected readonly checkedCount = computed(() => this.selectedClaims().filter((claim) => claim.status !== 'pending').length);

  // The track-record card counts what the Track record screen counts, where
  // unreviewed claims of a superseded version are not waiting on anyone.
  private readonly liveClaims = signal<PredictionClaim[]>([]);

  constructor() {
    inject(DestroyRef).onDestroy(() => this.stopElapsed());
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
    this.reviewError.set(null);
  }

  protected isLatest(reading: Reading): boolean {
    return this.readings()[0]?.id === reading.id;
  }

  protected async generate(): Promise<void> {
    const id = this.activeId();
    if (!id || this.generating()) return;
    const request = ++this.requestId;
    this.generating.set(true);
    this.startElapsed();
    this.generateError.set(null);
    this.reviewError.set(null);
    try {
      const generated = await this.readingsApi.generate(id, this.period(), true);
      if (request !== this.requestId || this.activeId() !== id) return;
      this.readings.update((items) => [generated, ...items.filter((item) => item.id !== generated.id)]);
      this.selectedId.set(generated.id);
      await this.loadClaims(id, request);
    } catch (error) {
      // The saved readings stay on screen; the failure sits above them with
      // a retry that tries the generation again, not a page reload.
      if (request === this.requestId) this.generateError.set((error as Error).message);
    } finally {
      if (request === this.requestId) {
        this.generating.set(false);
        this.stopElapsed();
      }
    }
  }

  /** Tapping the chosen answer again clears it, so a mis-tap is undoable. */
  protected async review(claim: PredictionClaim, status: PredictionClaimStatus): Promise<void> {
    const id = this.activeId();
    if (!id) return;
    const next: PredictionClaimStatus = claim.status === status ? 'pending' : status;
    this.savingId.set(claim.id);
    this.reviewError.set(null);
    try {
      const updated = await this.readingsApi.claimFeedback(id, claim.id, next, claim.user_feedback ?? '');
      if (this.activeId() !== id) return;
      const swap = (claims: PredictionClaim[]) => claims.map((item) => (item.id === updated.id ? { ...item, ...updated } : item));
      this.claims.update(swap);
      // A reviewed claim of an earlier version counts from now on.
      this.liveClaims.update((live) =>
        live.some((item) => item.id === updated.id) ? swap(live) : updated.status === 'pending' ? live : [...live, updated],
      );
    } catch (error) {
      this.reviewError.set((error as Error).message);
    } finally {
      if (this.savingId() === claim.id) this.savingId.set(null);
    }
  }

  protected trackLabel(): string {
    const reviewed = this.liveClaims().filter((claim) => claim.status !== 'pending' && claim.status !== 'not_applicable');
    if (!reviewed.length) return 'Your track record';
    const held = reviewed.filter((claim) => claim.status === 'accurate' || claim.status === 'partly').length;
    return `${held} of ${reviewed.length} ${reviewed.length === 1 ? 'prediction' : 'predictions'} held`;
  }

  protected trackSubcopy(): string {
    const today = new Date();
    const due = this.liveClaims().filter((claim) => claim.status === 'pending' && claimIsDue(claim, today)).length;
    if (due) return `${due} waiting for you to check`;
    if (this.liveClaims().length) return 'Nothing waiting to be checked';
    return 'Builds up as you check predictions';
  }

  protected readingTitle(reading: Reading): string {
    return reading.period_label ?? reading.generated_local_date ?? reading.reading_type;
  }

  protected stamp(reading: Reading): string {
    return reading.generated_at ? STAMP.format(new Date(reading.generated_at)) : '';
  }

  protected versionLine(reading: Reading): string {
    const stamp = this.stamp(reading);
    const version = `Version ${reading.version ?? 1}`;
    return stamp ? `${version} · Written ${stamp}` : version;
  }

  protected checkedLabel(reading: Reading): string {
    const claims = this.claims().filter((claim) => claim.reading_id === reading.id);
    if (!claims.length) return 'No predictions';
    return `${claims.filter((claim) => claim.status !== 'pending').length}/${claims.length} checked`;
  }

  protected askQuestion(reading: Reading): string {
    return `Explain my ${this.readingTitle(reading)} reading in simple terms and what I should do next`;
  }

  private startElapsed(): void {
    this.stopElapsed();
    const startedAt = Date.now();
    this.elapsed.set(0);
    this.elapsedTimer = setInterval(() => this.elapsed.set(Math.floor((Date.now() - startedAt) / 1000)), 1000);
  }

  private stopElapsed(): void {
    if (this.elapsedTimer !== null) clearInterval(this.elapsedTimer);
    this.elapsedTimer = null;
  }

  private async load(id: string | null, period: ReadingPeriod): Promise<void> {
    const request = ++this.requestId;
    // A profile or period switch supersedes any in-flight generation.
    this.generating.set(false);
    this.stopElapsed();
    this.loadError.set(null);
    this.generateError.set(null);
    this.reviewError.set(null);
    this.selectedId.set(null);
    this.readings.set([]);
    this.claims.set([]);
    this.liveClaims.set([]);
    if (!id) return;
    this.loading.set(true);
    try {
      const readings = await this.readingsApi.list(id, period);
      if (request !== this.requestId || this.activeId() !== id || this.period() !== period) return;
      this.readings.set(readings);
      this.selectedId.set(readings[0]?.id ?? null);
      await this.loadClaims(id, request);
    } catch (error) {
      if (request === this.requestId) this.loadError.set((error as Error).message);
    } finally {
      if (request === this.requestId) this.loading.set(false);
    }
  }

  private async loadClaims(id: string, request: number): Promise<void> {
    // Earlier versions keep their own predictions on screen, so ask for them.
    const [claims, live] = await Promise.all([
      this.readingsApi.claims(id, { includeSuperseded: true }),
      this.readingsApi.claims(id),
    ]);
    if (request !== this.requestId || this.activeId() !== id) return;
    this.claims.set(claims);
    this.liveClaims.set(live);
  }
}
