import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload, DashaPeriod, YoginiDashaPayload, YoginiDashaPeriod } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';

interface Period {
  name: string;
  dates: string;
  active?: boolean;
  source?: DashaPeriod | YoginiDashaPeriod;
}

interface ActivePeriodInsight {
  title: string;
  body: string;
  action: string;
  evidence: string;
}

/** Life Periods / Dashas (Figma node 40:87), Antar level. */
@Component({
  selector: 'as-life-periods',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './life-periods.component.html',
  styleUrl: './life-periods.component.scss',
})
export class LifePeriodsComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly preferences = inject(PreferencesService);
  protected readonly data = signal<DashaPayload | null>(null);
  protected readonly yogini = signal<YoginiDashaPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  readonly system = signal<'vimshottari' | 'yogini'>('vimshottari');
  readonly level = signal<'maha' | 'antar' | 'pratyantar' | 'sookshma' | 'prana'>('antar');

  readonly selectedMaha = signal<DashaPeriod | null>(null);
  readonly selectedAntar = signal<DashaPeriod | null>(null);

  // Sookshma/Prana are only computed along the *active* chain
  // (astrospace/core/vedic/dashas.py — a full 5-level tree for every branch
  // would be prohibitively large), so unlike Maha/Antar/Pratyantar these two
  // levels have no drill-into-an-arbitrary-period state of their own.
  readonly periods = computed(() => {
    if (this.system() === 'yogini') return (this.yogini()?.mahadashas ?? []).map((period) => this.toPeriod(period));
    if (this.level() === 'maha') return (this.data()?.mahadashas ?? []).map((period) => this.toPeriod(period));
    if (this.level() === 'pratyantar') return (this.selectedAntar()?.pratyantardashas ?? this.data()?.current.pratyantardashas ?? []).map((period) => this.toPeriod(period));
    if (this.level() === 'sookshma') return (this.data()?.current.sookshmadashas ?? []).map((period) => this.toPeriod(period));
    if (this.level() === 'prana') return (this.data()?.current.pranadashas ?? []).map((period) => this.toPeriod(period));
    return (this.selectedMaha()?.antardashas ?? this.data()?.current.mahadasha?.antardashas ?? []).map((period) => this.toPeriod(period));
  });
  readonly activePath = computed(() => {
    const current = this.data()?.current;
    return [current?.mahadasha?.lord, current?.antardasha?.lord, current?.pratyantardasha?.lord].filter(Boolean).join(' → ') || 'No active dasha';
  });
  readonly activeYogini = computed(() => this.yogini()?.current.mahadasha?.lord ?? this.yogini()?.mahadashas.find((period) => period.active)?.lord ?? 'No active Yogini');
  readonly activeInsight = computed<ActivePeriodInsight>(() => {
    if (this.system() === 'yogini') {
      const lord = this.activeYogini();
      return {
        title: `${lord} is the background rhythm`,
        body: this.yoginiMeaning(lord),
        action: this.periodAction(lord),
        evidence: 'Yogini dasha is shown as a secondary 36-year cycle. Use it as confirmation, not as a replacement for the Vimshottari stack.',
      };
    }
    const current = this.data()?.current;
    const chain = [
      current?.mahadasha?.lord,
      current?.antardasha?.lord,
      current?.pratyantardasha?.lord,
      current?.sookshmadasha?.lord,
      current?.pranadasha?.lord,
    ].filter(Boolean) as string[];
    const lead = current?.mahadasha?.lord ?? chain[0] ?? 'Current';
    const near = current?.pratyantardasha?.lord ?? current?.antardasha?.lord ?? lead;
    return {
      title: `${lead} sets the chapter; ${near} colors the moment`,
      body: `${this.periodMeaning({ name: lead, dates: '' })} ${near !== lead ? this.periodMeaning({ name: near, dates: '' }) : ''}`.trim(),
      action: this.periodAction(near),
      evidence: `Active stack: ${chain.join(' → ') || 'not returned'} · ${this.asOfLabel(this.data()?.as_of)} · Moon nakshatra balance`,
    };
  });
  readonly mahaCrumb = computed(() => this.selectedMaha()?.lord ?? this.data()?.current.mahadasha?.lord ?? 'selected maha');
  readonly antarCrumb = computed(() => this.selectedAntar()?.lord ?? this.data()?.current.antardasha?.lord ?? 'selected antar');
  readonly pratyantarCrumb = computed(() => this.data()?.current.pratyantardasha?.lord ?? 'selected pratyantar');
  readonly sookshmaCrumb = computed(() => this.data()?.current.sookshmadasha?.lord ?? 'selected sookshma');

  // Sookshma/Prana are Practitioner-only — Balanced keeps the three-level
  // stack it already had; only Practitioner gets the full five.
  readonly levelTabs = computed(() =>
    ['maha', 'antar', 'pratyantar', 'sookshma', 'prana'] as const,
  );

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected chooseSystem(system: 'vimshottari' | 'yogini'): void {
    this.system.set(system);
    this.resetScroll();
  }

  protected chooseLevel(level: 'maha' | 'antar' | 'pratyantar' | 'sookshma' | 'prana'): void {
    this.system.set('vimshottari');
    this.level.set(level);
    this.resetScroll();
  }

  protected drill(period: Period): void {
    if (this.system() === 'yogini') return;
    const source = period.source as DashaPeriod | undefined;
    if (this.level() === 'maha' && source?.antardashas?.length) {
      this.selectedMaha.set(source);
      this.selectedAntar.set(source.antardashas.find((row) => row.active) ?? source.antardashas[0] ?? null);
      this.level.set('antar');
    } else if (this.level() === 'antar' && source?.pratyantardashas?.length) {
      this.selectedAntar.set(source);
      this.level.set('pratyantar');
    }
    this.resetScroll();
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.data.set(null);
        this.yogini.set(null);
        return;
      }
      const cached = this.vedic.cachedAll(activeId);
      const [dashas, yogini] = await Promise.all([
        cached?.dashas ? Promise.resolve(cached.dashas) : this.vedic.dashas(activeId),
        this.vedic.yoginiDashas(activeId).catch(() => null),
      ]);
      this.data.set(dashas);
      this.yogini.set(yogini);
      const maha = dashas.current.mahadasha ?? dashas.mahadashas[0] ?? null;
      const antar = dashas.current.antardasha ?? maha?.antardashas?.[0] ?? null;
      this.selectedMaha.set(maha);
      this.selectedAntar.set(antar);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private toPeriod(period: DashaPeriod | YoginiDashaPeriod): Period {
    return {
      name: period.lord,
      dates: `${this.dateLabel(period.start)}–${this.dateLabel(period.end)}`,
      active: period.active,
      source: period,
    };
  }

  protected periodMeaning(period: Period): string {
    const lord = period.name.toLowerCase();
    if (lord.includes('sun') || lord.includes('surya')) return 'A visibility period: identity, authority, confidence and responsibility need conscious handling.';
    if (lord.includes('moon') || lord.includes('chandra')) return 'An emotional period: family, mood, memory and belonging become louder than usual.';
    if (lord.includes('mars') || lord.includes('mangal')) return 'An action period: courage is useful, but impatience can create unnecessary conflict.';
    if (lord.includes('mercury') || lord.includes('budha')) return 'A learning period: communication, trade, study and decisions benefit from precision.';
    if (lord.includes('jupiter') || lord.includes('guru')) return 'A growth period: teachers, faith, children, counsel and long-range choices come forward.';
    if (lord.includes('venus') || lord.includes('shukra')) return 'A relationship period: comfort, love, art, money and agreement need better balance.';
    if (lord.includes('saturn') || lord.includes('shani')) return 'A discipline period: slow work, commitments and maturity matter more than quick wins.';
    if (lord.includes('rahu')) return 'A change period: ambition and unfamiliar paths rise, so check promises before following them.';
    if (lord.includes('ketu')) return 'A simplification period: detachment, spiritual focus and closure can become more important.';
    return 'A timing chapter: read it with the house, planet strength and current transits before making a conclusion.';
  }

  protected yoginiMeaning(lord: string): string {
    const key = lord.toLowerCase();
    if (key.includes('mangala')) return 'Mangala brings action and heat. It is useful for courage, but asks you to avoid rushing people or decisions.';
    if (key.includes('pingala')) return 'Pingala turns attention toward visibility, health of pride, authority, and how you carry responsibility.';
    if (key.includes('dhanya')) return 'Dhanya is a growth and nourishment period. Learning, support, family and prosperity themes can become more available.';
    if (key.includes('bhramari')) return 'Bhramari can feel restless or corrective. It asks for patience, cleaner habits, and fewer scattered commitments.';
    if (key.includes('bhadrika')) return 'Bhadrika supports steadier gains, social help, refinement and practical improvement.';
    if (key.includes('ulka')) return 'Ulka can expose pressure points. Keep decisions grounded and do not let anxiety choose the path.';
    if (key.includes('siddha')) return 'Siddha favors completion, skill, spiritual effort and practical mastery. Use it to finish what has already matured.';
    if (key.includes('sankata')) return 'Sankata asks for resilience. It is not a punishment, but a period to simplify, protect energy, and move carefully.';
    return 'This Yogini period should be read as a background rhythm and cross-checked with the active Vimshottari period and current transits.';
  }

  protected periodAction(lord: string): string {
    const key = lord.toLowerCase();
    if (key.includes('sun') || key.includes('surya') || key.includes('pingala')) return 'Lead with humility. Take responsibility, but do not turn every situation into a test of pride.';
    if (key.includes('moon') || key.includes('chandra')) return 'Protect sleep, family rhythm, and emotional steadiness before making big choices.';
    if (key.includes('mars') || key.includes('mangal')) return 'Use energy for disciplined action. Delay arguments and impulsive commitments.';
    if (key.includes('mercury') || key.includes('budha')) return 'Write things down, verify details, and make communication precise.';
    if (key.includes('jupiter') || key.includes('guru') || key.includes('dhanya')) return 'Seek counsel, teach what you know, and choose the option that grows well over time.';
    if (key.includes('venus') || key.includes('shukra') || key.includes('bhadrika')) return 'Repair agreements, choose beauty with discipline, and avoid comfort becoming excess.';
    if (key.includes('saturn') || key.includes('shani') || key.includes('sankata')) return 'Make the plan smaller and more consistent. Slow progress is still progress here.';
    if (key.includes('rahu') || key.includes('bhramari')) return 'Question glamour and urgency. New paths are fine when promises are checked.';
    if (key.includes('ketu') || key.includes('ulka') || key.includes('siddha')) return 'Simplify, finish, and let go of what no longer has life in it.';
    return 'Use this period as timing context, then check house placement, strength and transits before acting.';
  }

  private dateLabel(value: string): string {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  private asOfLabel(value?: string): string {
    if (!value) return 'current date';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  private resetScroll(): void {
    requestAnimationFrame(() => this.host.nativeElement.scrollIntoView({ block: 'start' }));
  }
}
