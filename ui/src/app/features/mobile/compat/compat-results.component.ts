import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { CompatibilityPayload } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';

@Component({
  selector: 'as-compat-results',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mcor-back" [routerLink]="['/m','compat']"><img src="mobile/back.svg" alt="" /><span>Compatibility</span></a>
    <main class="mcor-body">
      @if (loading()) {
        <section class="mcor-state"><b>Computing match</b><p>Calculating Gun Milan from both saved profiles.</p></section>
      } @else if (error()) {
        <section class="mcor-state error" role="alert">
          <b>Compatibility could not load</b>
          <p>{{ error() }}</p>
          <button type="button" (click)="reload()">Retry</button>
        </section>
      } @else if (!partnerId()) {
        <section class="mcor-state"><b>Select a person</b><p>Choose or add another profile before viewing results.</p><a [routerLink]="['/m','compat']">Choose person</a></section>
      } @else if (score(); as s) {
        <section class="mcor-score"><b>{{ activeName() }} x {{ partnerName() }}</b><div><strong>{{ s.total }}</strong><span>/ {{ s.max }}</span></div><h1>{{ s.verdict }}</h1><p>{{ s.percent }}% from {{ s.rows.length }} returned koota rows.</p></section>
        <p class="mcor-title">WHAT MATTERS MOST HERE</p>
        <section class="mcor-list">@for (row of visibleKootas(); track row.label) { <div><b>{{ row.label }}</b><span>{{ row.points }} / {{ row.max }}</span><p>{{ row.note }}</p></div> }</section>
        @if (preferences.experienceMode() === 'practitioner') {
          <p class="mcor-title">INPUTS &amp; CANCELLATIONS</p>
          <section class="mcor-flag"><p>{{ s.system }} · active profile {{ activeName() }} · partner {{ partnerName() }}</p></section>
        }
        <p class="mcor-title">NOTES FROM CALCULATION</p>
        <section class="mcor-flag">
          @for (note of s.notes ?? []; track note) { <p>{{ note }}</p> }
          @if (!(s.notes ?? []).length) { <p>No additional backend notes were returned.</p> }
        </section>
        <div class="mcor-actions"><button type="button" (click)="share()">{{ shared() ? 'Copied' : 'Share report' }}</button><a [routerLink]="['/m','compat','results','detail']" [queryParams]="{ partner: partnerId() }">Full detail</a></div>
        <a class="mcor-muhurta" [routerLink]="['/m','muhurta']">Find a muhurtham</a>
      }
    </main>
  `,
  styleUrl: './compat-results.component.scss',
})
export class CompatResultsComponent {
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
      this.score.set(await this.vedic.compatibility(activeId, partnerId));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
