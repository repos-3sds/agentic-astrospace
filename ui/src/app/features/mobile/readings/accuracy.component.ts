import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';

import { HapticsService } from '../../../core/haptics.service';

import { KundliStore } from '../../../core/kundli.store';
import { PredictionClaim, PredictionClaimStatus } from '../../../core/models';
import { ReadingService } from '../../../core/reading.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { ClaimMarker, REVIEW_OPTIONS, claimIsDue, claimWindow } from './claim-review';

/** How long a just-marked card stays put under the finger before it folds away. */
export const SETTLE_MS = 600;
/** Matches the collapse transition in accuracy.component.scss. */
export const COLLAPSE_MS = 280;

const COUNT_STATUSES: Array<{ label: string; status: PredictionClaimStatus; tone: string }> = [
  ...REVIEW_OPTIONS,
  { label: 'Not checked yet', status: 'pending', tone: 'empty' },
];

@Component({
  selector: 'as-reading-accuracy',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, GenericErrorComponent],
  template: `
    <a class="mra-back" [asBack]="['/m','readings']"><img src="mobile/back.svg" alt="" /><span>Readings</span></a>
    <main class="mra-body">
      <header><h1>Track record</h1><p>How the predictions in your readings turned out, by your own account.</p></header>

      @if (loading()) {
        <section class="mra-state" aria-live="polite">
          <b>Loading claims</b>
          <p>Checking prediction claims for {{ activeName() }}.</p>
        </section>
      } @else if (error()) {
        <as-generic-error role="alert" [message]="error()!" (retried)="reload()" />
      } @else if (!activeId()) {
        <section class="mra-state">
          <b>No active profile</b>
          <p>Select a profile before reviewing accuracy.</p>
        </section>
      } @else {
        <section class="mra-summary">
          <div><span><b>{{ heldRateLabel() }}</b></span><small>{{ summaryLine() }}</small></div>
          <div class="mra-meter">
            @for (item of counts(); track item.label) {
              <i [attr.data-tone]="item.tone" [style.flex]="item.count || 0.0001"></i>
            }
          </div>
          <footer>
            @for (item of counts(); track item.label) {
              <span><i [attr.data-tone]="item.tone"></i>{{ item.label }} {{ item.count }}</span>
            }
          </footer>
        </section>

        <nav class="mra-tabs" aria-label="Claim filter">
          <button type="button" [class.on]="filter() === 'pending'" (click)="filter.set('pending')">To check ({{ dueClaims().length }})</button>
          <button type="button" [class.on]="filter() === 'all'" (click)="filter.set('all')">All</button>
        </nav>

        @if (!claims().length) {
          <section class="mra-state">
            <b>No predictions yet</b>
            <p>Get a reading first. Its predictions show up here so you can mark what happened.</p>
          </section>
        } @else {
          @if (filter() === 'pending') {
            <p class="mra-title accent">DID THESE HAPPEN?</p>
          } @else {
            <p class="mra-title">ALL PREDICTIONS</p>
          }

          @for (claim of visibleClaims(); track claim.id) {
            <div class="mra-slot" [class.collapsing]="collapsing().has(claim.id)">
            <section class="mra-claim" [class.reviewed]="claim.status !== 'pending'">
              <div>
                <em>{{ claim.category }}</em>
                <small>{{ claimWindow(claim) }}</small>
              </div>
              <blockquote>{{ claim.claim_text }}</blockquote>
              <p>{{ sourceLabel(claim) }}</p>
              <footer>
                @for (option of statuses; track option.status) {
                  <button
                    type="button"
                    [attr.data-tone]="option.tone"
                    [class.active]="claim.status === option.status"
                    [attr.aria-pressed]="claim.status === option.status"
                    [class.saving]="marker.isSaving(claim.id, option.status)"
                    [attr.aria-busy]="marker.isSaving(claim.id, option.status)"
                    (click)="review(claim, option.status)"
                  >{{ option.label }}</button>
                }
              </footer>
              @if (marker.errors()[claim.id]; as message) {
                <small class="mra-claim-error" role="alert">{{ message }}</small>
              }
            </section>
            </div>
          } @empty {
            <section class="mra-state">
              <b>Nothing to check right now</b>
              <p>{{ upcomingLine() }}</p>
            </section>
          }
        }
      }
    </main>
  `,
  styleUrl: './accuracy.component.scss',
})
export class AccuracyComponent {
  private readonly store = inject(KundliStore);
  private readonly readingsApi = inject(ReadingService);
  private requestId = 0;

  protected readonly statuses = REVIEW_OPTIONS;
  protected readonly claimWindow = claimWindow;
  protected readonly claims = signal<PredictionClaim[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  /** Marked in "To check" and still shown, so the card doesn't vanish under the finger. */
  protected readonly settling = signal<ReadonlySet<string>>(new Set());
  /** Folding away after the pause. */
  protected readonly collapsing = signal<ReadonlySet<string>>(new Set());
  private readonly timers = new Map<string, ReturnType<typeof setTimeout>[]>();
  private readonly haptics = inject(HapticsService);
  protected readonly marker = new ClaimMarker(this.readingsApi, (claimId, change) =>
    this.claims.update((claims) => claims.map((item) => (item.id === claimId ? { ...item, ...change } : item))),
  );
  protected readonly filter = signal<'pending' | 'all'>('pending');

  protected readonly activeId = computed(() => this.store.activeId());
  protected readonly activeName = computed(() => this.store.active()?.name ?? 'this profile');
  protected readonly visibleClaims = computed(() => {
    if (this.filter() !== 'pending') return this.claims();
    const today = new Date();
    const settling = this.settling();
    return this.claims().filter(
      (claim) => settling.has(claim.id) || (claim.status === 'pending' && claimIsDue(claim, today)),
    );
  });
  // A prediction is only asked about once its window has begun.
  protected readonly dueClaims = computed(() => {
    const today = new Date();
    return this.claims().filter((claim) => claim.status === 'pending' && claimIsDue(claim, today));
  });
  protected readonly counts = computed(() =>
    COUNT_STATUSES.map((status) => ({
      ...status,
      count: this.claims().filter((claim) => claim.status === status.status).length,
    })),
  );
  protected readonly totalClaims = computed(() => this.claims().length);
  protected readonly reviewedApplicable = computed(() =>
    this.claims().filter((claim) => claim.status === 'accurate' || claim.status === 'partly' || claim.status === 'missed'),
  );
  protected readonly heldClaims = computed(() =>
    this.reviewedApplicable().filter((claim) => claim.status === 'accurate' || claim.status === 'partly'),
  );

  constructor() {
    inject(DestroyRef).onDestroy(() => this.timers.forEach((list) => list.forEach(clearTimeout)));
    effect(() => {
      void this.load(this.activeId());
    });
  }

  protected reload(): void {
    void this.load(this.activeId());
  }

  /**
   * Optimistic: the answer shows at once and only the tapped chip says it is
   * saving. In "To check" a marked card used to disappear the moment the
   * answer came back and the next card slid under the finger (audit R7); it
   * now stays marked for a beat, then folds away.
   */
  protected async review(claim: PredictionClaim, status: PredictionClaimStatus): Promise<void> {
    const id = this.activeId();
    if (!id) return;
    this.haptics.select();
    const next: PredictionClaimStatus = claim.status === status ? 'pending' : status;
    if (this.filter() === 'pending' && next !== 'pending') this.settle(claim.id);
    else this.unsettle(claim.id);
    const saved = await this.marker.mark(id, claim, status);
    if (saved === null) this.unsettle(claim.id);
  }

  private settle(claimId: string): void {
    this.unsettle(claimId);
    this.settling.update((ids) => new Set(ids).add(claimId));
    this.timers.set(claimId, [
      setTimeout(() => this.collapsing.update((ids) => new Set(ids).add(claimId)), SETTLE_MS),
      setTimeout(() => this.unsettle(claimId), SETTLE_MS + COLLAPSE_MS),
    ]);
  }

  private unsettle(claimId: string): void {
    this.timers.get(claimId)?.forEach(clearTimeout);
    this.timers.delete(claimId);
    const without = (ids: ReadonlySet<string>) => {
      if (!ids.has(claimId)) return ids;
      const next = new Set(ids);
      next.delete(claimId);
      return next;
    };
    this.settling.update(without);
    this.collapsing.update(without);
  }

  protected heldRateLabel(): string {
    const applicable = this.reviewedApplicable().length;
    if (!applicable) return 'No checks yet';
    return `${Math.round((this.heldClaims().length / applicable) * 100)}%`;
  }

  protected summaryLine(): string {
    const applicable = this.reviewedApplicable().length;
    if (!applicable) return `${this.totalClaims()} predictions to follow`;
    return `${this.heldClaims().length} of ${applicable} held`;
  }

  protected upcomingLine(): string {
    const upcoming = this.claims().filter((claim) => claim.status === 'pending').length;
    if (upcoming) return `${upcoming} more will be ready to check once their dates arrive. They are listed under All.`;
    return 'You have checked every prediction so far.';
  }

  protected sourceLabel(claim: PredictionClaim): string {
    const kind = claim.reading_type ? `${claim.reading_type} reading` : 'reading';
    const version = claim.reading_version && claim.reading_version > 1 ? `, version ${claim.reading_version}` : '';
    return `From your ${kind}${version}`;
  }

  private async load(id: string | null): Promise<void> {
    const request = ++this.requestId;
    this.error.set(null);
    this.claims.set([]);
    this.marker.reset();
    this.timers.forEach((list) => list.forEach(clearTimeout));
    this.timers.clear();
    this.settling.set(new Set());
    this.collapsing.set(new Set());
    if (!id) return;
    this.loading.set(true);
    try {
      const claims = await this.readingsApi.claims(id);
      if (request !== this.requestId || this.activeId() !== id) return;
      this.claims.set(claims);
    } catch (error) {
      if (request === this.requestId) this.error.set((error as Error).message);
    } finally {
      if (request === this.requestId) this.loading.set(false);
    }
  }
}
