import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';

import { KundliStore } from '../../../core/kundli.store';
import { PredictionClaim, PredictionClaimStatus } from '../../../core/models';
import { ReadingService } from '../../../core/reading.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { REVIEW_OPTIONS, claimIsDue, claimWindow } from './claim-review';

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
                    [disabled]="savingId() === claim.id"
                    (click)="review(claim, option.status)"
                  >{{ option.label }}</button>
                }
              </footer>
            </section>
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
  protected readonly savingId = signal<string | null>(null);
  protected readonly filter = signal<'pending' | 'all'>('pending');

  protected readonly activeId = computed(() => this.store.activeId());
  protected readonly activeName = computed(() => this.store.active()?.name ?? 'this profile');
  protected readonly visibleClaims = computed(() =>
    this.filter() === 'pending' ? this.dueClaims() : this.claims(),
  );
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
    effect(() => {
      void this.load(this.activeId());
    });
  }

  protected reload(): void {
    void this.load(this.activeId());
  }

  protected async review(claim: PredictionClaim, status: PredictionClaimStatus): Promise<void> {
    const id = this.activeId();
    if (!id) return;
    this.savingId.set(claim.id);
    this.error.set(null);
    try {
      // Tapping the chosen answer again clears it, so a mis-tap is undoable.
      const next: PredictionClaimStatus = claim.status === status ? 'pending' : status;
      const updated = await this.readingsApi.claimFeedback(id, claim.id, next, claim.user_feedback ?? '');
      if (this.activeId() !== id) return;
      this.claims.update((claims) => claims.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      if (this.savingId() === claim.id) this.savingId.set(null);
    }
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
