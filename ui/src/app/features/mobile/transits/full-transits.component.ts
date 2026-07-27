import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { GocharamMatchedRule, GocharamProfilePayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { TransitDetail, TransitDetailComponent } from './transit-detail.component';

@Component({
  selector: 'as-full-transits',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, TransitDetailComponent],
  template: `
    <a class="mtrf-back" [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mtrf-body">
      <header><h1>Full Transits</h1><p>Gochara with vedha, Ashtakavarga and evidence</p></header>
      <nav class="mtrf-tabs"><a [routerLink]="['/m','transits']">Gochara</a><span>Full Transits</span></nav>
      @if (loading()) {
        <section class="mtrf-copy"><p>Calculating all nine placements…</p></section>
      } @else if (error()) {
        <section class="mtrf-copy"><p>{{ error() }}</p><button type="button" (click)="load()">Try again</button></section>
      } @else if (data(); as payload) {
        <p class="mtrf-title">CURRENT POSITIONS · EFFECTIVE VERDICT</p>
        <section class="mtrf-list">
          @for (rule of baselineRules(); track rule.rule_id) {
            <button type="button" (click)="open(rule)">
              <span><b>{{ rule.planet }}</b><small>{{ payload.gochara.planets[rule.planet].sign }} · house {{ rule.house }}</small></span>
              <em>AV {{ av(rule)?.['bindus'] ?? '—' }}</em>
              @if (hasVedha(rule)) { <i>VEDHA</i> }
            </button>
          }
        </section>
        <p class="mtrf-title">SPECIAL OVERLAYS</p>
        <section class="mtrf-copy">
          @for (rule of specialRules(); track rule.rule_id) {
            <p><b>{{ rule.rule_name }}</b> — {{ rule.content.balanced_context }}</p>
          } @empty {
            <p>No named special overlay is active.</p>
          }
        </section>
        <p class="mtrf-title">ACTIVE WINDOWS</p>
        <section class="mtrf-events">
          @for (window of payload.gochara.timeline.active_windows; track window.rule + window.start_date) {
            <div [attr.data-tone]="window.tone === 'supportive' ? 'good' : 'warn'"><i></i><small>{{ window.planet }}</small><p>{{ window.rule }} · {{ window.start_date }} → {{ window.end_date }}</p></div>
          }
        </section>
        <p class="mtrf-title">CONVENTION</p>
        <section class="mtrf-copy"><p>{{ payload.gochara.interpretation.convention.node_treatment }}</p><p>{{ payload.gochara.interpretation.convention.safety }}</p></section>
      }
    </main>
    @if(selected()){<as-transit-detail [detail]="selected()!" (dismissed)="selected.set(null)" />}
  `,
  styleUrl: './full-transits.component.scss',
})
export class FullTransitsComponent {
  private readonly store = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  readonly data = signal<GocharamProfilePayload | null>(null);
  readonly selected = signal<TransitDetail | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly profileId = computed(() => this.store.activeId());
  readonly baselineRules = computed(() => this.data()?.gochara.interpretation.matched_rules.filter((rule) => rule.kind === 'baseline_placement') ?? []);
  readonly specialRules = computed(() => this.data()?.gochara.interpretation.matched_rules.filter((rule) => rule.kind === 'special_overlay') ?? []);

  constructor() {
    effect(() => {
      const id = this.profileId();
      if (id) void this.load(id);
    });
  }

  protected async load(id = this.profileId()): Promise<void> {
    if (!id) return;
    this.loading.set(true);
    this.error.set(null);
    try {
      this.data.set(await this.vedic.gocharam(id, 90));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected av(rule: GocharamMatchedRule): Record<string, unknown> | null {
    return rule.modifiers.find((row) => row.type === 'ashtakavarga')?.evidence ?? null;
  }
  protected hasVedha(rule: GocharamMatchedRule): boolean {
    return rule.modifiers.some((row) => row.type === 'vedha');
  }
  protected open(rule: GocharamMatchedRule): void {
    const payload = this.data();
    if (!payload) return;
    this.selected.set({
      planet: `${rule.planet} transit`,
      glyph: rule.planet.slice(0, 2),
      position: `${payload.gochara.planets[rule.planet].sign} · house ${rule.house} from Moon`,
      period: rule.duration.replaceAll('_', ' '),
      meaning: rule.content.practitioner_deep_dive,
      guidance: `Base ${rule.base_verdict}; effective ${rule.effective_verdict}.`,
      evidence: rule.modifiers.map((row) => `${row.type}: ${row.label}`).concat(`${rule.source_id} · ${rule.source_status}`),
    });
  }
}
