import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import {
  AshtakavargaTransitPlanet,
  ClassicalGocharaStatus,
  GocharamMatchedRule,
  GocharamProfilePayload,
} from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
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
      <header><h1>Full Transits</h1><p>Current sky with practical meaning first, evidence second</p></header>
      <nav class="mtrf-tabs"><a [routerLink]="['/m','transits']">Gochara</a><span>Full Transits</span></nav>
      @if (loading()) {
        <section class="mtrf-copy"><p>Calculating all nine placements…</p></section>
      } @else if (error()) {
        <section class="mtrf-copy"><p>{{ error() }}</p><button type="button" (click)="load()">Try again</button></section>
      } @else if (data(); as payload) {
        @if (sadeSati(); as sade) {
          <p class="mtrf-title">SADE SATI</p>
          <section class="mtrf-copy" [attr.data-tone]="sade.active ? 'warn' : 'good'">
            <p><b>{{ sade.active ? 'Active' : 'Not active' }}</b>@if (sade.active && sade.phase) { — {{ sade.phase }} phase }</p>
            <p>{{ sade.active ? 'Use this as a discipline marker: simplify commitments, protect sleep, and do the slow necessary work.' : 'Saturn is not pressing the natal Moon through Sade Sati right now.' }}</p>
            <p>Evidence: Saturn is {{ sade.saturn_house_from_moon }} house(s) from your natal Moon.</p>
          </section>
        }
        <p class="mtrf-title">{{ payload.gochara.interpretation.range_outlook.days }}-DAY RANGE</p>
        <section class="mtrf-copy">
          <p><b>{{ payload.gochara.interpretation.range_outlook.title }}</b></p>
          <p>{{ payload.gochara.interpretation.range_outlook.reading }}</p>
        </section>
        <p class="mtrf-title">CURRENT POSITIONS · WHAT TO WATCH</p>
        <section class="mtrf-list">
          @for (rule of baselineRules(); track rule.rule_id) {
            <button type="button" (click)="open(rule)">
              <span><b>{{ rule.planet }}</b><small>{{ transitPlain(rule) }}</small><small class="mtrf-action">{{ ruleAction(rule) }}</small></span>
              <em>AV {{ avRow(rule)?.bindus ?? '—' }}</em>
              @if (hasVedha(rule)) { <i>VEDHA</i> }
              @if (classicalFor(rule); as classical) {
                @if (!classical.favourable) { <i data-tone="warn">UNFAVOURABLE</i> }
              }
            </button>
          }
        </section>
        <p class="mtrf-title">SPECIAL OVERLAYS</p>
        <section class="mtrf-copy">
          @for (rule of specialRules(); track rule.rule_id) {
            <p><b>{{ rule.rule_name }}</b> — {{ content(rule) }}</p>
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
  protected readonly preferences = inject(PreferencesService);
  readonly data = signal<GocharamProfilePayload | null>(null);
  readonly selected = signal<TransitDetail | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly profileId = computed(() => this.store.activeId());
  readonly baselineRules = computed(() => this.data()?.gochara.interpretation?.matched_rules.filter((rule) => rule.kind === 'baseline_placement') ?? []);
  readonly specialRules = computed(() => this.data()?.gochara.interpretation?.matched_rules.filter((rule) => rule.kind === 'special_overlay') ?? []);
  readonly sadeSati = computed(() => this.data()?.gochara.sade_sati ?? null);
  private readonly classicalGochara = computed<Record<string, ClassicalGocharaStatus>>(
    () => this.data()?.gochara.classical_gochara ?? {},
  );
  private readonly ashtakavargaByPlanet = computed<Record<string, AshtakavargaTransitPlanet>>(
    () => this.data()?.gochara.ashtakavarga?.planets ?? this.data()?.ashtakavarga_transit?.planets ?? {},
  );

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

  /** Real typed BAV/SAV/kakshya row, replacing the old untyped grab from
   * modifiers[].evidence — matches gochara.component.ts's approach. */
  protected avRow(rule: GocharamMatchedRule): AshtakavargaTransitPlanet | null {
    return this.ashtakavargaByPlanet()[rule.planet] ?? null;
  }
  protected classicalFor(rule: GocharamMatchedRule): ClassicalGocharaStatus | null {
    return this.classicalGochara()[rule.planet] ?? null;
  }
  protected hasVedha(rule: GocharamMatchedRule): boolean {
    return rule.modifiers.some((row) => row.type === 'vedha');
  }

  /** Mode-aware copy (US-GOC-028): mirrors gochara.component.ts's content()
   * so Full Transits stops always showing dense practitioner text. */
  protected content(rule: GocharamMatchedRule): string {
    if (this.preferences.experienceMode() === 'guided') return rule.content.guided_summary;
    if (this.preferences.experienceMode() === 'practitioner') return rule.content.practitioner_deep_dive;
    return rule.content.balanced_context;
  }

  protected transitPlain(rule: GocharamMatchedRule): string {
    const house = rule.house ? `house ${rule.house}` : 'its current place';
    const verdict = rule.effective_verdict === 'supportive' ? 'supportive' : 'needs care';
    return `${house} · ${verdict} · tap for evidence`;
  }

  protected ruleAction(rule: GocharamMatchedRule): string {
    const theme = this.houseTheme(rule.house);
    if (rule.effective_verdict === 'supportive') return `Use for ${theme}, without forcing speed.`;
    if (this.hasVedha(rule)) return `A block is present: double-check ${theme} before committing.`;
    return `Watch ${theme}; choose patience over reaction.`;
  }

  private houseTheme(house: number): string {
    return ({
      1: 'body, mood and direction',
      2: 'money, speech and family',
      3: 'effort, skills and communication',
      4: 'home and emotional ground',
      5: 'learning and creativity',
      6: 'health routines and disputes',
      7: 'partnerships and agreements',
      8: 'shared resources and repair',
      9: 'belief, teachers and travel',
      10: 'work and reputation',
      11: 'gains and networks',
      12: 'rest, expenses and release',
    } as Record<number, string>)[Number(house)] ?? 'the activated life area';
  }

  protected open(rule: GocharamMatchedRule): void {
    const payload = this.data();
    if (!payload) return;
    this.selected.set({
      planet: `${rule.planet} transit`,
      glyph: rule.planet.slice(0, 2),
      position: `${payload.gochara.planets[rule.planet]?.sign ?? '—'} · house ${rule.house} from Moon`,
      period: rule.duration.replaceAll('_', ' '),
      meaning: this.content(rule),
      guidance: `Base ${rule.base_verdict}; effective ${rule.effective_verdict}.`,
      evidence: rule.modifiers
        .map((row) => `${row.type}: ${row.label}`)
        .concat(`${rule.source_id} · ${rule.source_status}`),
    });
  }
}
