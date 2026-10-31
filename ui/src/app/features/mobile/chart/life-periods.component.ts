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
import { BackBarComponent } from '../shared/back-bar.component';
import { BirthTimeBadgeComponent } from './birth-time-badge.component';
import { dayMonthYear, monthYear } from '../format-date';
import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload, DashaPeriod, DashaVariantKey, DashaVariantPayload, YoginiDashaPayload, YoginiDashaPeriod } from '../../../core/models';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { SelectHapticDirective } from '../shared/select-haptic.directive';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PlanLockComponent } from '../shared/plan-lock.component';
import { StickyBarDirective } from '../shared/sticky-bar.directive';

interface Period {
  name: string;
  dates: string;
  active?: boolean;
  source?: DashaPeriod | YoginiDashaPeriod;
}

type VimshottariStart = 'standard' | DashaVariantKey;

/** The Practitioner "Start from" list; labels follow astrospace/core/vedic/dasha_variants.py. */
const VIMSHOTTARI_STARTS: readonly { key: VimshottariStart; label: string; seed: string }[] = [
  { key: 'standard', label: 'Moon star (standard)', seed: 'Moon nakshatra balance' },
  { key: 'tribhagi', label: 'Tribhagi (40-year cycle)', seed: 'Moon nakshatra balance, each period a third as long' },
  { key: 'kshema', label: 'Kshema Tara (4th star)', seed: 'started from Kshema Tara, the 4th star from the Moon' },
  { key: 'utpanna', label: 'Utpanna Tara (5th star)', seed: 'started from Utpanna Tara, the 5th star from the Moon' },
  { key: 'adhana', label: 'Adhana Tara (8th star)', seed: 'started from Adhana Tara, the 8th star from the Moon' },
  { key: 'd1_lagna', label: 'D1 Lagna', seed: 'started from the D1 Lagna' },
  { key: 'd9_lagna', label: 'D9 Lagna', seed: 'started from the D9 (Navamsha) Lagna' },
  { key: 'd10_lagna', label: 'D10 Lagna', seed: 'started from the D10 (Dashamsha) Lagna' },
];

/** One row of the Practitioner period tree: Maha, Antar or Pratyantar. */
interface TreeRow {
  key: string;
  level: 0 | 1 | 2;
  lord: string;
  start: string;
  end: string;
  age: string;
  active: boolean;
  expandable: boolean;
  open: boolean;
}

interface ChainRow {
  level: string;
  lord: string;
  start: string;
  end: string;
}

interface ActivePeriodInsight {
  title: string;
  body: string;
  action: string;
  evidence: string;
}

/** Life Periods / Dashas (Figma node 40:87), Antar level. */
type DashaLevel = 'maha' | 'antar' | 'pratyantar' | 'sookshma' | 'prana';

@Component({
  selector: 'as-life-periods',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StickyBarDirective, BackBarComponent, GenericErrorComponent, RouterLink, BirthTimeBadgeComponent, SelectHapticDirective, PlanLockComponent],
  templateUrl: './life-periods.component.html',
  styleUrl: './life-periods.component.scss',
})
export class LifePeriodsComponent {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  protected readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  protected readonly preferences = inject(PreferencesService);
  private readonly gate = inject(PlanGateService);
  /** Free and testers see the current Maha and Antar dasha; deeper levels and Yogini are Plus. */
  protected readonly full = computed(() => this.gate.allows('dashas.full'));
  /** Vimshottari from another starting point, or Tribhagi: Practitioner plan only. */
  protected readonly variantsAllowed = computed(() => this.gate.allows('dashas.variants'));
  protected readonly starts = VIMSHOTTARI_STARTS;
  readonly start = signal<VimshottariStart>('standard');
  protected readonly variantLoading = signal(false);
  protected readonly variantError = signal<string | null>(null);
  /** The standard Moon-star dasha, kept so switching back costs nothing. */
  private standard: DashaPayload | null = null;
  protected readonly data = signal<DashaPayload | null>(null);
  protected readonly variantNote = computed(() => (this.data() as DashaVariantPayload | null)?.observance_note ?? null);
  protected readonly startOption = computed(() => VIMSHOTTARI_STARTS.find((row) => row.key === this.start()) ?? VIMSHOTTARI_STARTS[0]);
  protected readonly yogini = signal<YoginiDashaPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  readonly system = signal<'vimshottari' | 'yogini'>('vimshottari');
  readonly level = signal<DashaLevel>('antar');

  /** Practitioner sees one dense screen: the active chain, then an inline tree. */
  protected readonly practitioner = computed(() => this.preferences.experienceMode() === 'practitioner');
  /** Tree rows opened by tap, keyed by level and start; the active chain opens itself. */
  private readonly opened = signal<ReadonlySet<string>>(new Set());

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
    const chain = [current?.mahadasha?.lord, current?.antardasha?.lord, this.full() ? current?.pratyantardasha?.lord : null];
    return chain.filter(Boolean).join(' → ') || 'No active dasha';
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
    ].slice(0, this.full() ? 5 : 2).filter(Boolean) as string[];
    const lead = current?.mahadasha?.lord ?? chain[0] ?? 'Current';
    const near = (this.full() ? current?.pratyantardasha?.lord : null) ?? current?.antardasha?.lord ?? lead;
    return {
      title: `${lead} sets the chapter; ${near} colors the moment`,
      body: `${this.periodMeaning({ name: lead, dates: '' })} ${near !== lead ? this.periodMeaning({ name: near, dates: '' }) : ''}`.trim(),
      action: this.periodAction(near),
      evidence: `Active stack: ${chain.join(' → ') || 'not returned'} · ${this.asOfLabel(this.data()?.as_of)} · ${this.startOption().seed}`,
    };
  });
  readonly chain = computed<ChainRow[]>(() => {
    const row = (level: string, period?: { lord: string; start: string; end: string } | null): ChainRow | null =>
      period ? { level, lord: period.lord, start: dayMonthYear(period.start), end: dayMonthYear(period.end) } : null;
    if (this.system() === 'yogini') {
      const current = this.yogini()?.current;
      return [row('Maha', current?.mahadasha), row('Antar', current?.antardasha)].filter(Boolean) as ChainRow[];
    }
    const current = this.data()?.current;
    return [
      row('Maha', current?.mahadasha),
      row('Antar', current?.antardasha),
      row('Pratyantar', current?.pratyantardasha),
      row('Sookshma', current?.sookshmadasha),
      row('Prana', current?.pranadasha),
    ].slice(0, this.full() ? 5 : 2).filter(Boolean) as ChainRow[];
  });

  readonly tree = computed<TreeRow[]>(() => {
    type Node = { lord: string; start: string; end: string; active: boolean; antardashas?: Node[]; pratyantardashas?: Node[] };
    const mahas: Node[] = this.system() === 'yogini' ? (this.yogini()?.mahadashas ?? []) : (this.data()?.mahadashas ?? []);
    const birth = mahas[0] ? new Date(mahas[0].start).getTime() : NaN;
    const opened = this.opened();
    const maxLevel = this.system() === 'yogini' || !this.full() ? 1 : 2;
    const rows: TreeRow[] = [];
    const walk = (nodes: Node[], level: 0 | 1 | 2): void => {
      for (const node of nodes) {
        const key = `${level}:${node.start}`;
        const children = level === 0 ? node.antardashas : level === 1 ? node.pratyantardashas : undefined;
        const expandable = level < maxLevel && !!children?.length;
        const open = expandable && (opened.has(key) ? !node.active : node.active);
        rows.push({
          key, level, lord: node.lord, active: node.active, expandable, open,
          start: dayMonthYear(node.start), end: dayMonthYear(node.end),
          age: this.ageAt(node.start, birth),
        });
        if (open && children) walk(children, (level + 1) as 1 | 2);
      }
    };
    walk(mahas, 0);
    return rows;
  });

  protected toggle(row: TreeRow): void {
    if (!row.expandable) return;
    const next = new Set(this.opened());
    if (next.has(row.key)) next.delete(row.key);
    else next.add(row.key);
    this.opened.set(next);
  }

  private ageAt(start: string, birth: number): string {
    const years = (new Date(start).getTime() - birth) / (365.25 * 86400000);
    return Number.isFinite(years) ? `${Math.max(0, Math.floor(years))}` : '';
  }

  readonly mahaCrumb = computed(() => this.selectedMaha()?.lord ?? this.data()?.current.mahadasha?.lord ?? 'selected maha');
  readonly antarCrumb = computed(() => this.selectedAntar()?.lord ?? this.data()?.current.antardasha?.lord ?? 'selected antar');
  readonly pratyantarCrumb = computed(() => this.data()?.current.pratyantardasha?.lord ?? 'selected pratyantar');
  readonly sookshmaCrumb = computed(() => this.data()?.current.sookshmadasha?.lord ?? 'selected sookshma');

  // The comment here always said Sookshma/Prana were Practitioner-only, but
  // every mode got all five. Guided now sees chapters and sub-periods,
  // Balanced the three-level stack, and Practitioner the full five.
  readonly levelTabs = computed<readonly DashaLevel[]>(() => {
    const mode = this.preferences.experienceMode();
    if (mode === 'guided' || !this.full()) return ['maha', 'antar'];
    if (mode === 'practitioner') return ['maha', 'antar', 'pratyantar', 'sookshma', 'prana'];
    return ['maha', 'antar', 'pratyantar'];
  });

  protected levelLabel(level: DashaLevel): string {
    if (this.preferences.experienceMode() === 'guided') return level === 'maha' ? 'Chapters' : 'Sub-periods';
    return { maha: 'Maha', antar: 'Antar', pratyantar: 'Pratyantar', sookshma: 'Sookshma', prana: 'Prana' }[level];
  }

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

  protected async chooseStart(key: VimshottariStart): Promise<void> {
    this.start.set(key);
    this.variantError.set(null);
    const activeId = this.kundlis.activeId();
    if (key === 'standard' || !activeId) {
      if (this.standard) this.showDashas(this.standard);
      return;
    }
    this.variantLoading.set(true);
    try {
      const payload = await this.vedic.dashaVariant(activeId, key);
      if (this.start() === key && this.kundlis.activeId() === activeId) this.showDashas(payload);
    } catch (error) {
      if (this.start() !== key) return;
      this.variantError.set((error as Error).message || 'Could not compute this dasha.');
      this.start.set('standard');
      if (this.standard) this.showDashas(this.standard);
    } finally {
      this.variantLoading.set(false);
    }
  }

  private showDashas(dashas: DashaPayload): void {
    this.data.set(dashas);
    this.opened.set(new Set());
    const maha = dashas.current.mahadasha ?? dashas.mahadashas[0] ?? null;
    const antar = dashas.current.antardasha ?? maha?.antardashas?.[0] ?? null;
    this.selectedMaha.set(maha);
    this.selectedAntar.set(antar);
  }

  protected chooseLevel(level: DashaLevel): void {
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
    } else if (this.level() === 'antar' && source?.pratyantardashas?.length && this.levelTabs().includes('pratyantar')) {
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
        this.standard = null;
        this.data.set(null);
        this.yogini.set(null);
        return;
      }
      const cached = this.vedic.cachedAll(activeId);
      const [dashas, yogini] = await Promise.all([
        cached?.dashas ? Promise.resolve(cached.dashas) : this.vedic.dashas(activeId),
        this.vedic.yoginiDashas(activeId).catch(() => null),
      ]);
      this.standard = dashas;
      this.start.set('standard');
      this.variantError.set(null);
      this.yogini.set(yogini);
      this.showDashas(dashas);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private toPeriod(period: DashaPeriod | YoginiDashaPeriod): Period {
    return {
      name: period.lord,
      dates: `${monthYear(period.start)}–${monthYear(period.end)}`,
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
