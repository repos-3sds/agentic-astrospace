import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { CompatibilityPayload } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PlanLockComponent } from '../shared/plan-lock.component';

@Component({
  selector: 'as-compat-results',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PlanLockComponent, BackLinkDirective, GenericErrorComponent, RouterLink],
  template: `
    <a class="mcor-back" [asBack]="['/m','compat']"><img src="mobile/back.svg" alt="" /><span>Compatibility</span></a>
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
        <section class="mcor-score"><b>{{ activeName() }} x {{ partnerName() }}</b><div><strong>{{ s.total }}</strong><span>/ {{ s.max }}</span></div><h1>{{ s.verdict }}</h1><p>{{ s.percent }}% across the eight kootas.</p></section>
        @if (!fullReport()) {
          <as-plan-lock
            from="compatibility.full"
            title="The full report"
            body="Each of the eight kootas, what matters most for this pair, the notes behind the score, and a shareable report."
          />
          <a class="mcor-muhurta" [routerLink]="['/m','muhurta']">Find a muhurtham</a>
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
        <div class="mcor-actions"><button type="button" (click)="share()">{{ shared() ? 'Copied' : 'Share report' }}</button><a [routerLink]="['/m','compat','results','detail']" [queryParams]="{ partner: partnerId() }">Full detail</a></div>
        <a class="mcor-muhurta" [routerLink]="['/m','muhurta']">Find a muhurtham</a>
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
      this.score.set(await this.vedic.compatibility(activeId, partnerId));
      this.gate.recordCompatibility(partnerId);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
