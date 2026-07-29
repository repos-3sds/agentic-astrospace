import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { PredictionClaim, PredictionClaimStatus } from '../../../core/models';
import { ReadingService } from '../../../core/reading.service';

const REVIEW_STATUSES: Array<{ label: string; status: PredictionClaimStatus; tone: string }> = [
  { label: 'accurate', status: 'accurate', tone: 'good' },
  { label: 'partly', status: 'partly', tone: 'warn' },
  { label: 'missed', status: 'missed', tone: 'bad' },
  { label: 'n/a', status: 'not_applicable', tone: 'neutral' },
];

const COUNT_STATUSES: Array<{ label: string; status: PredictionClaimStatus; tone: string }> = [
  { label: 'pending', status: 'pending', tone: 'neutral' },
  ...REVIEW_STATUSES,
];

@Component({
  selector: 'as-reading-accuracy',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mra-back" [routerLink]="['/m','readings']"><img src="mobile/back.svg" alt="" /><span>Readings</span></a>
    <main class="mra-body">
      <header><h1>Track record</h1><p>Only returned prediction claims are counted here.</p></header>

      @if (loading()) {
        <section class="mra-state" aria-live="polite">
          <b>Loading claims</b>
          <p>Checking prediction claims for {{ activeName() }}.</p>
        </section>
      } @else if (error()) {
        <section class="mra-state error" role="alert">
          <b>Claims could not load</b>
          <p>{{ error() }}</p>
          <button type="button" (click)="reload()">Retry</button>
        </section>
      } @else if (!activeId()) {
        <section class="mra-state">
          <b>No active profile</b>
          <p>Select a profile before reviewing accuracy.</p>
        </section>
      } @else {
        <section class="mra-summary">
          <div><span><b>{{ heldRateLabel() }}</b></span><small>{{ totalClaims() }} claims returned</small></div>
          <div class="mra-meter">
            @for (item of counts(); track item.label) {
              <i [attr.data-tone]="item.tone" [style.flex]="item.count || 0.0001"></i>
            }
          </div>
          <footer>
            @for (item of counts(); track item.label) {
              <span><i [attr.data-tone]="item.tone"></i>{{ item.count }} {{ item.label }}</span>
            }
          </footer>
        </section>

        <nav class="mra-tabs" aria-label="Claim filter">
          <button type="button" [class.on]="filter() === 'pending'" (click)="filter.set('pending')">To review</button>
          <button type="button" [class.on]="filter() === 'all'" (click)="filter.set('all')">All</button>
        </nav>

        @if (!claims().length) {
          <section class="mra-state">
            <b>No claims returned</b>
            <p>Generate a reading first, then return here after claims are available.</p>
          </section>
        } @else {
          @if (filter() === 'pending') {
            <p class="mra-title accent">AWAITING YOUR CALL</p>
          } @else {
            <p class="mra-title">ALL CLAIMS</p>
          }

          @for (claim of visibleClaims(); track claim.id) {
            <section class="mra-claim" [class.reviewed]="claim.status !== 'pending'">
              <div>
                <em>{{ claim.category }}</em>
                <small>{{ claimWindow(claim) }}</small>
              </div>
              <blockquote>{{ claim.claim_text }}</blockquote>
              <p>Status: {{ claimStatusLabel(claim.status) }}</p>
              <footer>
                @for (option of statuses; track option.status) {
                  <button
                    type="button"
                    [class.active]="claim.status === option.status"
                    [disabled]="savingId() === claim.id"
                    (click)="review(claim, option.status)"
                  >{{ option.label }}</button>
                }
              </footer>
            </section>
          } @empty {
            <section class="mra-state">
              <b>No pending claims</b>
              <p>All returned claims for this profile have a review status.</p>
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

  protected readonly statuses = REVIEW_STATUSES;
  protected readonly claims = signal<PredictionClaim[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly savingId = signal<string | null>(null);
  protected readonly filter = signal<'pending' | 'all'>('pending');

  protected readonly activeId = computed(() => this.store.activeId());
  protected readonly activeName = computed(() => this.store.active()?.name ?? 'this profile');
  protected readonly visibleClaims = computed(() =>
    this.filter() === 'pending'
      ? this.claims().filter((claim) => claim.status === 'pending')
      : this.claims(),
  );
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
      const updated = await this.readingsApi.claimFeedback(id, claim.id, status, claim.user_feedback ?? '');
      if (this.activeId() !== id) return;
      this.claims.update((claims) => claims.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      if (this.savingId() === claim.id) this.savingId.set(null);
    }
  }

  protected heldRateLabel(): string {
    const applicable = this.reviewedApplicable().length;
    if (!applicable) return '-';
    return `${Math.round((this.heldClaims().length / applicable) * 100)}%`;
  }

  protected claimStatusLabel(status: PredictionClaimStatus): string {
    if (status === 'not_applicable') return 'N/A';
    return status.replace('_', ' ');
  }

  protected claimWindow(claim: PredictionClaim): string {
    if (!claim.target_start_date) return claim.period_label ?? 'undated';
    if (!claim.target_end_date || claim.target_end_date === claim.target_start_date) {
      return claim.target_start_date;
    }
    return `${claim.target_start_date} to ${claim.target_end_date}`;
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
