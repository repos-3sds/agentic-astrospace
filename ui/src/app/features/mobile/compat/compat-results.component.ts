import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { EntitlementLimitError } from '../../../core/entitlement-denial';
import { KundliStore } from '../../../core/kundli.store';
import { CompatibilityPayload } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PlanLockComponent } from '../shared/plan-lock.component';
import { StickyBarDirective } from '../shared/sticky-bar.directive';

@Component({
  selector: 'as-compat-results',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StickyBarDirective, PlanLockComponent, BackLinkDirective, GenericErrorComponent, RouterLink],
  template: `
    <a class="mcor-back" asStickyBar [asBack]="['/m','compat']"><img src="mobile/back.svg" alt="" /><span>Compatibility</span></a>
    <main class="mcor-body">
      @if (loading()) {
        <section class="mcor-state"><b>Computing match</b><p>Calculating Gun Milan from both saved profiles.</p></section>
      } @else if (error()) {
        <as-generic-error role="alert" [message]="error()!" (retried)="reload()" />
      } @else if (!partnerId()) {
        <section class="mcor-state"><b>Select a person</b><p>Choose or add another profile before viewing results.</p><a [routerLink]="['/m','compat']">Choose person</a></section>
      } @else if (overLimit()) {
        <as-plan-lock
          from="compatibility.checks.period"
          title="This month’s free match is used"
          body="Free includes one compatibility score a month, and you can reopen that one any time. Plus checks as many people as you like, with the full report."
        />
      } @else if (score(); as s) {
        @if (marriageMatch()) {
          <!-- Varna and Vashya are read from the groom's side (U16). -->
          <div class="mcor-side" role="radiogroup" aria-label="Who is the groom?">
            <span>Groom</span>
            <button type="button" role="radio" [attr.aria-checked]="!partnerIsGroom()" [class.on]="!partnerIsGroom()" (click)="setGroom(false)">{{ activeName() }}</button>
            <button type="button" role="radio" [attr.aria-checked]="partnerIsGroom()" [class.on]="partnerIsGroom()" (click)="setGroom(true)">{{ partnerName() }}</button>
          </div>
        }
        <section class="mcor-score"><b>{{ activeName() }} x {{ partnerName() }}</b><div><strong>{{ s.total }}</strong><span>/ {{ s.max }}</span></div><h1>{{ s.verdict }}</h1><p>{{ s.percent }}% across the eight kootas.</p></section>
        @if (!fullReport()) {
          <as-plan-lock
            from="compatibility.full"
            title="The full report"
            body="Each of the eight kootas, what matters most for this pair, the notes behind the score, and a shareable report."
          />
          <a class="mcor-muhurta" [routerLink]="['/m','muhurta']">Find a muhurta</a>
        } @else {
        <p class="mcor-title">WHAT MATTERS MOST HERE</p>
        <section class="mcor-list">@for (row of visibleKootas(); track row.label) { <div><b>{{ row.label }}</b><span>{{ row.points }} / {{ row.max }}</span><p>{{ row.note }}</p></div> }</section>
        @if (preferences.experienceMode() === 'practitioner') {
          <p class="mcor-title">INPUTS &amp; CANCELLATIONS</p>
          <section class="mcor-flag"><p>{{ s.system }} · active profile {{ activeName() }} · partner {{ partnerName() }}</p></section>
        }
        <p class="mcor-title">HOW THIS WAS SCORED</p>
        <section class="mcor-flag">
          @if (!marriageMatch()) { <p>Ashta Koota comes from marriage matching. For {{ partnerName() }}, read it as a rough guide to how you get along.</p> }
          @for (note of s.notes ?? []; track note) { <p>{{ note }}</p> }
        </section>
        <div class="mcor-actions"><button type="button" (click)="share()">{{ shared() ? 'Copied' : 'Share report' }}</button><a [routerLink]="['/m','compat','results','detail']" [queryParams]="{ partner: partnerId(), groom: partnerIsGroom() ? 'partner' : null }">What helps, in full</a></div>
        <a class="mcor-muhurta" [routerLink]="['/m','muhurta']">Find a muhurta</a>
        }
      }
    </main>
  `,
  styleUrl: './compat-results.component.scss',
})
export class CompatResultsComponent {
  protected readonly gate = inject(PlanGateService);
  protected readonly preferences = inject(PreferencesService);
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly route = inject(ActivatedRoute);

  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly score = signal<CompatibilityPayload | null>(null);
  protected readonly shared = signal(false);
  protected readonly partnerId = signal(this.route.snapshot.queryParamMap.get('partner'));
  protected readonly partner = computed(() => this.kundlis.kundlis().find((profile) => profile.id === this.partnerId()) ?? null);
  protected readonly activeName = computed(() => this.kundlis.active()?.name ?? 'You');
  protected readonly partnerName = computed(() => this.partner()?.name ?? 'Selected person');
  /** Free shows the score; Plus shows the report behind it. */
  protected readonly fullReport = computed(() => this.gate.allows('compatibility.full'));
  protected readonly overLimit = signal(false);
  /** Classical matching reads from the groom's side; it was always the reader's. */
  protected readonly partnerIsGroom = signal(this.route.snapshot.queryParamMap.get('groom') === 'partner');
  /** Gun Milan is a marriage system; anyone else gets told how to read it. */
  protected readonly marriageMatch = computed(() =>
    ['spouse', 'partner', 'prospect'].includes(this.partner()?.relation ?? 'partner'));
  protected readonly visibleKootas = computed(() => {
    const rows = this.score()?.rows ?? [];
    return this.preferences.experienceMode() === 'practitioner' ? rows : rows.slice(0, 4);
  });

  constructor() {
    void this.load();
  }

  protected setGroom(partner: boolean): void {
    if (partner === this.partnerIsGroom()) return;
    this.partnerIsGroom.set(partner);
    void this.load();
  }

  protected reload(): void {
    void this.load();
  }

  protected share(): void {
    const score = this.score();
    if (!score) return;
    void navigator.clipboard?.writeText(`${this.activeName()} x ${this.partnerName()}: ${score.total} / ${score.max}`);
    this.shared.set(true);
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
      // Free: one person a month, counted by partner so reopening is free.
      if (!this.gate.allowsCompatibility(partnerId)) {
        this.overLimit.set(true);
        return;
      }
      const groomFirst = this.partnerIsGroom() && this.marriageMatch();
      this.score.set(groomFirst
        ? await this.vedic.compatibility(partnerId, activeId)
        : await this.vedic.compatibility(activeId, partnerId));
      this.gate.recordCompatibility(partnerId);
    } catch (error) {
      // The server keeps the real count (sweep G-6); the phone's is a hint.
      if (error instanceof EntitlementLimitError) this.overLimit.set(true);
      else this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
