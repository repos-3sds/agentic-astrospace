import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Injector,
  afterNextRender,
  computed,
  effect,
  inject,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import { HapticsService } from '../../../core/haptics.service';
import { KundliStore } from '../../../core/kundli.store';
import { PredictionClaim, PredictionClaimStatus, Reading } from '../../../core/models';
import { ReadingPeriod, ReadingService } from '../../../core/reading.service';
import { MarkdownPipe } from '../../../shared/markdown.pipe';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SheetComponent } from '../sheet/sheet.component';
import { SelectHapticDirective } from '../shared/select-haptic.directive';
import { ClaimMarker, REVIEW_OPTIONS, claimIsDue, claimWindow } from './claim-review';
import { GenerationJob, ReadingGenerationService, generationKey } from './reading-generation.service';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PlanLockComponent } from '../shared/plan-lock.component';

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

/** "this week", "Past weeks": how a period is named in a sentence and in a list title. */
const PERIOD_UNIT: Record<ReadingPeriod, { current: string; past: string; one: string }> = {
  daily: { current: 'today', past: 'Past days', one: 'day' },
  weekly: { current: 'this week', past: 'Past weeks', one: 'week' },
  monthly: { current: 'this month', past: 'Past months', one: 'month' },
  quarterly: { current: 'this quarter', past: 'Past quarters', one: 'quarter' },
  yearly: { current: 'this year', past: 'Past years', one: 'year' },
};

const STAMP = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
const SHORT_DAY = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' });
const WEEKDAY = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
const MONTH = new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' });

function parseDay(value: string): Date {
  const [y, m, d] = value.split('-').map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

/** "Oct 12 – 18", or "Sep 28 – Oct 4" across a month. */
export function dayRange(start: string, end: string): string {
  const a = parseDay(start);
  const b = parseDay(end);
  const format = SHORT_DAY as Intl.DateTimeFormat & { formatRange?: (x: Date, y: Date) => string };
  if (typeof format.formatRange === 'function') return format.formatRange(a, b);
  return `${SHORT_DAY.format(a)} – ${SHORT_DAY.format(b)}`;
}

/** The calendar period a reading covers, named by its dates. */
export function periodTitle(reading: Reading): string {
  const start = reading.period_start;
  const end = reading.period_end;
  if (start && end) {
    switch (reading.reading_type) {
      case 'daily': return WEEKDAY.format(parseDay(start));
      case 'weekly': return dayRange(start, end);
      case 'monthly': return MONTH.format(parseDay(start));
      case 'yearly': return String(parseDay(start).getFullYear());
    }
  }
  return reading.period_label ?? reading.generated_local_date ?? reading.reading_type;
}

/**
 * Splits a period's readings into versions of the period the person is in
 * now and readings of earlier periods. Until 2026-10-15 every row was
 * treated as a version of the current reading, so three different weeks
 * showed as "Version 1 / Version 1 / Version 1" and yesterday's daily
 * reading as today's "Latest" (production audit R2). The server says which
 * rows are current; an older server that doesn't is read as "the newest
 * row's label is the current one".
 */
export function splitReadings(readings: Reading[]): { current: Reading[]; past: Reading[] } {
  const flagged = readings.some((reading) => typeof reading.is_current_period === 'boolean');
  const newestLabel = readings[0]?.period_label;
  const isCurrent = (reading: Reading) =>
    flagged ? reading.is_current_period === true : reading.period_label === newestLabel;
  const byVersion = (a: Reading, b: Reading) =>
    (b.version ?? 1) - (a.version ?? 1) || (b.generated_at ?? '').localeCompare(a.generated_at ?? '');
  const byPeriod = (a: Reading, b: Reading) =>
    (b.period_start ?? b.generated_local_date ?? '').localeCompare(a.period_start ?? a.generated_local_date ?? '') || byVersion(a, b);
  return {
    current: readings.filter(isCurrent).sort(byVersion),
    past: readings.filter((reading) => !isCurrent(reading)).sort(byPeriod),
  };
}

@Component({
  selector: 'as-mobile-readings',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PlanLockComponent, BackLinkDirective, GenericErrorComponent, RouterLink, MarkdownPipe, SheetComponent, SelectHapticDirective],
  template: `
    <a class="mrd-back" [asBack]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mrd-body">
      <header><h1>Readings</h1><p>What your chart points to, and a record of what actually happened.</p></header>
      @if (!gate.allows('readings.full')) {
        <as-plan-lock
          from="readings.full"
          title="Weekly, monthly and yearly readings"
          body="A reading for each period from your dasha and transits, with a record of which of its claims came true."
        />
      } @else {

      <a class="mrd-track" [routerLink]="['/m','readings','accuracy']">
        <span>↗</span>
        <span><b>{{ trackLabel() }}</b><small>{{ trackSubcopy() }}</small></span>
        <img src="mobile/chevron.svg" alt="" />
      </a>

      <nav class="mrd-tabs" asSelectHaptic aria-label="Reading period" [attr.aria-busy]="loading()">
        @for (tab of periods; track tab.value) {
          <button type="button" [class.on]="period() === tab.value" [attr.aria-pressed]="period() === tab.value"
            [disabled]="loading()" (click)="choosePeriod(tab.value)">
            {{ tab.label }}
          </button>
        }
      </nav>

      @if (generateError(); as message) {
        @if (generateLimited()) {
          <!-- The daily allowance, not a failure: nothing to retry today. -->
          <section class="mrd-state" role="status">
            <b>No more new versions today</b>
            <p>{{ message }}</p>
          </section>
        } @else {
          <section class="mrd-state error" role="alert">
            <b>That reading didn’t finish</b>
            <p>{{ message }}</p>
            <button type="button" (click)="generate(lastForce)">Try again</button>
          </section>
        }
      }

      @if (generating()) {
        <section class="mrd-progress" role="status" aria-live="polite">
          <div class="mrd-progress-head">
            <span class="mrd-spinner" aria-hidden="true"></span>
            <span>
              <b>Writing {{ job()?.force ? 'a new version of ' : '' }}your {{ periodNoun() }} reading</b>
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
            <p>Taking a little longer than usual. It keeps going if you leave this screen.</p>
          } @else if (selected()) {
            <p>Your current reading stays below until the new one is ready.</p>
          }
        </section>
      }

      @if (loading()) {
        <section class="mrd-state" aria-live="polite">
          <b>Loading readings</b>
          <p>Checking saved readings for {{ activeName() }}.</p>
        </section>
      } @else if (loadError()) {
        <as-generic-error role="alert" [message]="loadError()!" (retried)="reload()" />
      } @else if (!activeId()) {
        <section class="mrd-state">
          <b>No active profile</b>
          <p>Create or select a profile to get readings.</p>
        </section>
      } @else {
        @if (!current().length && !generating() && !generateError()) {
          <section class="mrd-state">
            <b>No {{ periodNoun() }} reading for {{ unit().current }} yet</b>
            <p>Get a {{ periodNoun() }} reading for {{ activeName() }}. Its predictions will be listed below it so you can check them as the days pass.</p>
            <button type="button" (click)="generate(false)">Get my {{ periodNoun() }} reading</button>
          </section>
        }

        @if (selected(); as reading) {
          <!-- Re-created per reading so a swap fades in instead of jumping. -->
          @for (shown of [reading]; track shown.id) {
            <article #article class="mrd-reading" [attr.aria-label]="titleFor(shown)">
              @if (!isLatestCurrent(shown)) {
                <div class="mrd-older" role="note">
                  <span>{{ olderNote(shown) }}</span>
                  @if (current().length) {
                    <button type="button" (click)="select(current()[0].id)">Show latest</button>
                  }
                </div>
              }
              <div class="mrd-reading-head">
                <b>{{ titleFor(shown) }}</b>
                <em [class.latest]="isLatestCurrent(shown)">{{ badgeFor(shown) }}</em>
              </div>
              <div class="mrd-prose m-selectable" [innerHTML]="shown.content | markdown"></div>
              <hr />
              <footer><small>{{ versionLine(shown) }}</small></footer>
            </article>
          }

          <div class="mrd-actions">
            <a [routerLink]="['/m','ask']" [queryParams]="{ q: askQuestion(reading) }">Ask about this</a>
            @if (isCurrent(reading)) {
              <button type="button" [disabled]="generating()" (click)="confirmNewVersion()">New version</button>
            }
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
                <p class="m-selectable">{{ claim.claim_text }}</p>
                <div class="mrd-chips" role="group" [attr.aria-label]="'Did this happen? ' + claim.claim_text">
                  @for (option of reviewOptions; track option.status) {
                    <button type="button" [attr.data-tone]="option.tone"
                      [class.on]="claim.status === option.status"
                      [class.saving]="marker.isSaving(claim.id, option.status)"
                      [attr.aria-pressed]="claim.status === option.status"
                      [attr.aria-busy]="marker.isSaving(claim.id, option.status)"
                      (click)="review(claim, option.status)">{{ option.label }}</button>
                  }
                </div>
                @if (marker.errors()[claim.id]; as message) {
                  <small class="mrd-claim-error" role="alert">{{ message }}</small>
                }
              </article>
            } @empty {
              <p>This reading has no specific predictions to check.</p>
            }
          </section>
        }

        @if (current().length > 1) {
          <p class="mrd-title">VERSIONS OF {{ unit().current.toUpperCase() }}</p>
          @for (item of current(); track item.id; let first = $first) {
            <button class="mrd-earlier" type="button" [class.on]="item.id === selected()?.id"
              [attr.aria-current]="item.id === selected()?.id ? 'true' : null" (click)="select(item.id)">
              <span>
                <b>Version {{ item.version ?? 1 }}@if (first) { (latest)}</b>
                <small>Written {{ stamp(item) }}</small>
              </span>
              <em>{{ item.id === selected()?.id ? 'Viewing' : checkedLabel(item) }}</em>
              <img src="mobile/chevron.svg" alt="" />
            </button>
          }
        }

        @if (past().length) {
          <p class="mrd-title">{{ unit().past.toUpperCase() }}</p>
          @for (item of past(); track item.id) {
            <button class="mrd-earlier" type="button" [class.on]="item.id === selected()?.id"
              [attr.aria-current]="item.id === selected()?.id ? 'true' : null" (click)="select(item.id)">
              <span>
                <b>{{ periodTitle(item) }}</b>
                <small>@if (versionsOfLabel(item) > 1) {Version {{ item.version ?? 1 }} · }Written {{ stamp(item) }}</small>
              </span>
              <em>{{ item.id === selected()?.id ? 'Viewing' : checkedLabel(item) }}</em>
              <img src="mobile/chevron.svg" alt="" />
            </button>
          }
        }
      }
      }
    </main>

    @if (confirming()) {
      <as-sheet label="Write a new version" (dismissed)="confirming.set(false)">
        <div class="mrd-confirm">
          <h2>Write a new version?</h2>
          <p>It takes about 30 seconds, and this version stays in your list.</p>
          <button type="button" class="primary" (click)="startNewVersion()">Write new version</button>
          <button type="button" class="secondary" (click)="confirming.set(false)">Keep this one</button>
        </div>
      </as-sheet>
    }
  `,
  styleUrl: './readings.component.scss',
})
export class ReadingsComponent {
  protected readonly gate = inject(PlanGateService);
  private readonly store = inject(KundliStore);
  private readonly readingsApi = inject(ReadingService);
  private readonly generation = inject(ReadingGenerationService);
  private readonly haptics = inject(HapticsService);
  private readonly injector = inject(Injector);
  private requestId = 0;

  protected readonly periods = PERIODS;
  protected readonly stages = GENERATE_STAGES;
  protected readonly slowAfter = GENERATE_SLOW_AFTER;
  protected readonly reviewOptions = REVIEW_OPTIONS;
  protected readonly window = claimWindow;
  protected readonly periodTitle = periodTitle;
  protected readonly period = signal<ReadingPeriod>('weekly');
  protected readonly readings = signal<Reading[]>([]);
  protected readonly claims = signal<PredictionClaim[]>([]);
  protected readonly selectedId = signal<string | null>(null);
  protected readonly loading = signal(false);
  protected readonly loadError = signal<string | null>(null);
  protected readonly generateError = signal<string | null>(null);
  protected readonly generateLimited = signal(false);
  protected readonly confirming = signal(false);
  protected lastForce = false;
  private readonly now = signal(Date.now());
  private readonly article = viewChild<ElementRef<HTMLElement>>('article');

  protected readonly activeId = computed(() => this.store.activeId());
  protected readonly activeName = computed(() => this.store.active()?.name ?? 'this profile');
  protected readonly periodNoun = computed(() => PERIOD_NOUN[this.period()]);
  protected readonly unit = computed(() => PERIOD_UNIT[this.period()]);

  /** The generation for this profile and period, held above the screen so it
   * survives leaving it (production audit R6). */
  protected readonly job = computed<GenerationJob | null>(() => {
    const id = this.activeId();
    return id ? this.generation.jobs()[generationKey(id, this.period())] ?? null : null;
  });
  protected readonly generating = computed(() => this.job()?.status === 'running');
  protected readonly elapsed = computed(() => {
    const job = this.job();
    return job?.status === 'running' ? Math.max(0, Math.floor((this.now() - job.startedAt) / 1000)) : 0;
  });
  protected readonly stageIndex = computed(() => {
    const seconds = this.elapsed();
    let index = 0;
    GENERATE_STAGES.forEach((stage, i) => { if (seconds >= stage.after) index = i; });
    return index;
  });
  // Eases towards 95% and never claims completion until the API answers.
  protected readonly progress = computed(() => Math.round(95 * (1 - Math.exp(-this.elapsed() / 18))));

  private readonly split = computed(() => splitReadings(this.readings()));
  protected readonly current = computed(() => this.split().current);
  protected readonly past = computed(() => this.split().past);
  protected readonly selected = computed<Reading | null>(
    () => this.readings().find((reading) => reading.id === this.selectedId()) ?? this.current()[0] ?? null,
  );
  protected readonly selectedClaims = computed(() => {
    const readingId = this.selected()?.id;
    return readingId ? this.claims().filter((claim) => claim.reading_id === readingId) : [];
  });
  protected readonly checkedCount = computed(() => this.selectedClaims().filter((claim) => claim.status !== 'pending').length);

  // The track-record card counts what the Track record screen counts, where
  // unreviewed claims of a superseded version are not waiting on anyone.
  private readonly liveClaims = signal<PredictionClaim[]>([]);

  protected readonly marker = new ClaimMarker(this.readingsApi, (claimId, change) => {
    const swap = (claims: PredictionClaim[]) => claims.map((item) => (item.id === claimId ? { ...item, ...change } : item));
    this.claims.update(swap);
    // A reviewed claim of an earlier version counts from now on.
    this.liveClaims.update((live) => {
      if (live.some((item) => item.id === claimId)) return swap(live);
      const claim = this.claims().find((item) => item.id === claimId);
      return claim && claim.status !== 'pending' ? [...live, claim] : live;
    });
  });

  constructor() {
    effect(() => {
      const id = this.activeId();
      const period = this.period();
      void this.load(id, period);
    });
    // Ticks the elapsed counter only while a generation is running.
    effect((onCleanup) => {
      if (!this.generating()) return;
      this.now.set(Date.now());
      const timer = setInterval(() => this.now.set(Date.now()), 1000);
      onCleanup(() => clearInterval(timer));
    });
    // A generation that finished, here or while the person was elsewhere,
    // is picked up once the saved list is on screen.
    effect(() => {
      const job = this.job();
      if (!job || job.status === 'running' || this.loading()) return;
      untracked(() => this.settle(job));
    });
  }

  protected reload(): void {
    void this.load(this.activeId(), this.period());
  }

  protected choosePeriod(period: ReadingPeriod): void {
    if (period === this.period()) return;
    this.haptics.select();
    this.period.set(period);
  }

  /**
   * Show another reading. The lists below never reorder; the one being read
   * is marked instead. Until 2026-10-15 the tapped card vanished and the
   * page above was rewritten out of view (audit R3), so the article's top is
   * now brought into view inside the shell's scroller.
   */
  protected select(id: string): void {
    this.haptics.select();
    this.selectedId.set(id);
    this.scrollToArticle();
  }

  protected isCurrent(reading: Reading): boolean {
    return this.current().some((item) => item.id === reading.id);
  }

  protected isLatestCurrent(reading: Reading): boolean {
    return this.current()[0]?.id === reading.id;
  }

  protected confirmNewVersion(): void {
    this.haptics.tap();
    this.confirming.set(true);
  }

  protected startNewVersion(): void {
    this.confirming.set(false);
    this.generate(true);
  }

  /** The first reading of a period reuses a saved one; "New version" forces. */
  protected generate(force: boolean): void {
    const id = this.activeId();
    if (!id || this.generating()) return;
    this.haptics.press();
    this.lastForce = force;
    this.generateError.set(null);
    this.generateLimited.set(false);
    this.generation.start(id, this.period(), force);
  }

  protected review(claim: PredictionClaim, status: PredictionClaimStatus): void {
    const id = this.activeId();
    if (!id) return;
    this.haptics.select();
    void this.marker.mark(id, claim, status);
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

  /** "This week · Oct 12 – 18" for the current period, the dates alone for a past one. */
  protected titleFor(reading: Reading): string {
    const title = periodTitle(reading);
    if (!this.isCurrent(reading)) return title;
    const lead = this.unit().current;
    return `${lead.charAt(0).toUpperCase()}${lead.slice(1)} · ${title}`;
  }

  protected badgeFor(reading: Reading): string {
    if (this.isLatestCurrent(reading)) return 'Latest';
    if (this.isCurrent(reading)) return `Version ${reading.version ?? 1}`;
    return `Past ${this.unit().one}`;
  }

  protected olderNote(reading: Reading): string {
    if (this.isCurrent(reading)) return `An earlier version of ${this.unit().current}’s reading.`;
    return `A reading from a past ${this.unit().one}.`;
  }

  protected versionsOfLabel(reading: Reading): number {
    return this.readings().filter((item) => item.period_label === reading.period_label).length;
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
    return `Explain my ${reading.period_label ?? periodTitle(reading)} reading in simple terms and what I should do next`;
  }

  private scrollToArticle(): void {
    afterNextRender(() => {
      const element = this.article()?.nativeElement;
      if (!element) return;
      const reduce = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
      element.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    }, { injector: this.injector });
  }

  private settle(job: GenerationJob): void {
    this.generation.clear(job.kundliId, job.period);
    if (job.kundliId !== this.activeId() || job.period !== this.period()) return;
    if (job.status === 'error') {
      this.lastForce = job.force;
      this.generateLimited.set(job.errorStatus === 429);
      this.generateError.set(job.error ?? 'Your reading couldn’t be written just now.');
      this.haptics.error();
      return;
    }
    const reading = job.reading;
    if (!reading) return;
    this.generateError.set(null);
    this.readings.update((items) => [{ ...reading, is_current_period: true }, ...items.filter((item) => item.id !== reading.id)]);
    this.selectedId.set(reading.id);
    this.haptics.success();
    this.scrollToArticle();
    void this.loadClaims(job.kundliId, this.requestId);
  }

  private async load(id: string | null, period: ReadingPeriod): Promise<void> {
    const request = ++this.requestId;
    this.loadError.set(null);
    this.generateError.set(null);
    this.generateLimited.set(false);
    this.confirming.set(false);
    this.marker.reset();
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
