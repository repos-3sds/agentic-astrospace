import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { GocharamDomainReading, GocharamMatchedRule, GocharamProfilePayload } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { TransitDetail, TransitDetailComponent } from './transit-detail.component';

@Component({
  selector: 'as-gochara',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, TransitDetailComponent],
  template: `
    <a class="mtr-back" [routerLink]="['/m','chart']"><img src="mobile/back.svg" alt="" /><span>Your Chart</span></a>
    <main class="mtr-body">
      <header><h1>What’s moving now</h1><p>Current sky translated into everyday choices</p></header>
      <nav class="mtr-tabs"><span>Gochara</span><a [routerLink]="['/m','transits','full']">Full Transits</a></nav>
      @if (loading()) {
        <section class="mtr-overall"><b>CALCULATING</b><h2>Reading the current sky…</h2></section>
      } @else if (error()) {
        <section class="mtr-overall"><b>UNAVAILABLE</b><h2>Gocharam could not load</h2><p>{{ error() }}</p><button type="button" (click)="load()">Try again</button></section>
      } @else if (!profileId()) {
        <section class="mtr-overall"><b>BIRTH CHART NEEDED</b><h2>Add birth details first</h2><p>Gocharam needs a natal Moon and Lagna.</p><a [routerLink]="['/m','birth-details']">Create chart</a></section>
      } @else if (data(); as payload) {
        <section class="mtr-overall">
          <b>OVERALL · {{ payload.gochara.interpretation.synthesis.tone }}</b>
          <h2>{{ payload.gochara.interpretation.synthesis.headline }}</h2>
          <p>{{ summary() }}</p>
        </section>
        <p class="mtr-title">WHAT THIS MEANS FOR YOU · {{ payload.gochara.interpretation.range_outlook.days }} DAYS</p>
        @for (domain of domains(); track domain.id) {
          <button type="button" class="mtr-card" (click)="openDomain(domain)">
            <div>
              <b>{{ domain.title }}</b>
              <em [attr.data-tone]="domain.tone === 'supportive' ? 'good' : 'warn'">{{ domain.tone }}</em>
            </div>
            <small>{{ domain.main_theme }}</small>
            <p>{{ domainMeaning(domain) }}</p>
            <strong class="mtr-action">{{ domainAction(domain) }}</strong>
          </button>
        }
        <p class="mtr-title">PLANET DETAILS · OPTIONAL DEPTH</p>
        @for (rule of baselineRules(); track rule.rule_id) {
          <button type="button" class="mtr-card" (click)="open(rule)">
            <div>
              <b>{{ rule.planet }} in house {{ rule.house }}</b>
              <em [attr.data-tone]="tone(rule)">{{ rule.effective_verdict }}</em>
            </div>
            <small>{{ rule.rule_name }}</small>
            <p>{{ content(rule) }}</p>
            <strong class="mtr-action">{{ ruleAction(rule) }}</strong>
          </button>
        }
        <p class="mtr-hint">{{ payload.gochara.interpretation.library_version }} · Lahiri · {{ payload.node_type }} nodes</p>
      }
    </main>
    @if(selected()){<as-transit-detail [detail]="selected()!" (dismissed)="selected.set(null)" />}
  `,
  styleUrl: './gochara.component.scss',
})
export class GocharaComponent {
  private readonly store = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly preferences = inject(PreferencesService);
  readonly data = signal<GocharamProfilePayload | null>(null);
  readonly selected = signal<TransitDetail | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly profileId = computed(() => this.store.activeId());
  readonly baselineRules = computed(() =>
    this.data()?.gochara.interpretation.matched_rules.filter(
      (rule) => rule.kind === 'baseline_placement',
    ) ?? [],
  );
  readonly domains = computed(() => this.data()?.gochara.interpretation.domains ?? []);
  readonly summary = computed(() => {
    const synthesis = this.data()?.gochara.interpretation.synthesis;
    if (!synthesis) return '';
    if (this.preferences.experienceMode() === 'guided') return synthesis.guided_summary;
    if (this.preferences.experienceMode() === 'practitioner') return synthesis.practitioner_deep_dive;
    return synthesis.balanced_context;
  });

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

  protected content(rule: GocharamMatchedRule): string {
    if (this.preferences.experienceMode() === 'guided') return rule.content.guided_summary;
    if (this.preferences.experienceMode() === 'practitioner') return rule.content.practitioner_deep_dive;
    return rule.content.balanced_context;
  }

  protected domainMeaning(domain: GocharamDomainReading): string {
    const text = domain.reading || domain.range_outlook.reading || domain.main_theme;
    if (this.preferences.experienceMode() === 'practitioner') return text;
    return text
      .replace(/\bgochara\b/gi, 'current transit')
      .replace(/\bAV\b/g, 'support score')
      .replace(/\bvedha\b/gi, 'block')
      .replace(/\bMoon\b/g, 'emotional center');
  }

  protected domainAction(domain: GocharamDomainReading): string {
    const tone = domain.tone === 'supportive' ? 'Use this support' : 'Use care here';
    const planets = domain.leading_planets.length ? ` Leading signal: ${domain.leading_planets.join(', ')}.` : '';
    return `${tone}: ${domain.range_outlook.title}.${planets}`;
  }

  protected ruleAction(rule: GocharamMatchedRule): string {
    if (rule.effective_verdict === 'supportive') {
      return `Use it: let ${rule.planet} support ${this.houseTheme(rule.house)} without overextending.`;
    }
    return `Care point: slow down around ${this.houseTheme(rule.house)} and check decisions before acting.`;
  }

  protected houseTheme(house: number): string {
    return ({
      1: 'body, mood and direction',
      2: 'money, speech and family',
      3: 'effort, skills and communication',
      4: 'home, property and emotional ground',
      5: 'learning, creativity and children',
      6: 'health routines, service and conflict',
      7: 'partners, agreements and public dealings',
      8: 'shared resources, vulnerability and repair',
      9: 'teachers, travel and belief',
      10: 'work, reputation and responsibility',
      11: 'gains, networks and long-term aims',
      12: 'rest, expenses, retreat and release',
    } as Record<number, string>)[Number(house)] ?? 'the life area being activated';
  }

  protected tone(rule: GocharamMatchedRule): string {
    return rule.effective_verdict === 'supportive' ? 'good' : 'warn';
  }

  protected open(rule: GocharamMatchedRule): void {
    const payload = this.data();
    if (!payload) return;
    this.selected.set({
      planet: rule.rule_name,
      glyph: rule.planet.slice(0, 2),
      position: `${payload.gochara.planets[rule.planet]?.sign ?? ''} · ${rule.house} from Moon`,
      period: rule.duration.replaceAll('_', ' '),
      meaning: this.content(rule),
      guidance: `Base: ${rule.base_verdict}. Effective after modifiers: ${rule.effective_verdict}.`,
      evidence: [
        ...rule.modifiers.map((modifier) => `${modifier.type}: ${modifier.label}`),
        `${rule.source_id} · ${rule.claim_status}`,
        `${payload.ayanamsha} · ${payload.node_type} nodes`,
      ],
    });
  }

  protected openDomain(domain: GocharamDomainReading): void {
    const payload = this.data();
    if (!payload) return;
    this.selected.set({
      planet: domain.title,
      glyph: '✦',
      position: domain.main_theme,
      period: `${domain.range_outlook.days}-day domain outlook`,
      meaning: domain.reading,
      guidance: `${domain.range_outlook.title}. ${domain.range_outlook.reading}`,
      evidence: [
        `Leading planets: ${domain.leading_planets.join(', ')}`,
        ...domain.evidence_ids,
        `${payload.ayanamsha} · ${payload.node_type} nodes`,
      ],
    });
  }
}
