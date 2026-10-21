import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { PreferencesService } from '../../../core/preferences.service';
import { plannedTimingPlace } from '../../../core/timing-place';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { KundliStore } from '../../../core/kundli.store';
import { PanchangaCity } from '../../../core/models';
import { SelectHapticDirective } from '../shared/select-haptic.directive';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PlanLockComponent } from '../shared/plan-lock.component';
import { CityPickerComponent } from '../shared/city-picker.component';

/** Whose chart a purpose is timed to. Mirrors `whose` in core/vedic/muhurta.py. */
export type MuhurtaWhose = 'self' | 'child' | 'couple' | 'family' | 'mother';

/** One thing someone might be planning. */
export interface MuhurtaGoal {
  id: string;
  label: string;
  icon: string;
  detail: string;
  category: MuhurtaCategory;
  whose?: MuhurtaWhose;
  /** The goal observes Chaturmas, Kharmas and the like by default. */
  season?: boolean;
}

export type MuhurtaCategory = 'purchase' | 'home' | 'family' | 'work' | 'travel' | 'other';

/** How far out to search. `custom` hands off to a date picker; `date` is one fixed day. */
export type MuhurtaRange = 'week' | 'month' | 'fortnight' | 'custom' | 'date';

export const MUHURTA_GOALS: MuhurtaGoal[] = [
  { id: 'buy_vehicle', label: 'Vehicle', icon: 'goal-vehicle', detail: 'Buy or take delivery', category: 'purchase' },
  { id: 'buy_gold', label: 'Gold or jewellery', icon: 'goal-gold', detail: 'Purchase', category: 'purchase' },
  { id: 'buy_property_gold', label: 'Buy property', icon: 'goal-property', detail: 'House, flat or land', category: 'purchase' },
  { id: 'property_registration', label: 'Register property', icon: 'goal-contract', detail: 'At the sub-registrar', category: 'purchase' },
  { id: 'griha_pravesha', label: 'House warming', icon: 'goal-property', detail: 'Griha Pravesha', category: 'home', whose: 'family', season: true },
  { id: 'bhoomi_puja', label: 'Bhoomi puja', icon: 'goal-launch', detail: 'Start building', category: 'home', whose: 'family', season: true },
  { id: 'move_rented_home', label: 'Move to a rented home', icon: 'goal-journey', detail: 'Shifting house', category: 'home' },
  { id: 'marriage_related', label: 'Wedding', icon: 'goal-marriage', detail: 'Vivaha', category: 'family', whose: 'couple', season: true },
  { id: 'engagement', label: 'Engagement', icon: 'goal-marriage', detail: 'Nischitartham, roka', category: 'family', whose: 'couple', season: true },
  { id: 'seemantham', label: 'Baby shower', icon: 'goal-sacred', detail: 'Seemantham, godh bharai', category: 'family', whose: 'mother' },
  { id: 'namakarana', label: 'Naming ceremony', icon: 'goal-naming', detail: 'Namakarana', category: 'family', whose: 'child' },
  { id: 'annaprashana', label: 'First feeding', icon: 'goal-feeding', detail: 'Annaprashana', category: 'family', whose: 'child' },
  { id: 'mundan', label: 'First haircut', icon: 'topic-child', detail: 'Mundan, chudakarana', category: 'family', whose: 'child', season: true },
  { id: 'karnavedha', label: 'Ear piercing', icon: 'topic-child', detail: 'Karnavedha', category: 'family', whose: 'child' },
  { id: 'upanayana', label: 'Upanayana', icon: 'goal-sacred', detail: 'Sacred-thread ceremony', category: 'family', whose: 'child', season: true },
  { id: 'vidyarambha', label: 'Start learning', icon: 'goal-learning', detail: 'Vidyarambha, akshara', category: 'family', whose: 'child' },
  { id: 'start_venture', label: 'Shop or business', icon: 'goal-launch', detail: 'Opening day', category: 'work' },
  { id: 'join_job', label: 'Join a job', icon: 'topic-work', detail: 'First day', category: 'work' },
  { id: 'sign_contract', label: 'Sign a contract', icon: 'goal-contract', detail: 'Agreement or paperwork', category: 'work' },
  { id: 'start_journey', label: 'Start a journey', icon: 'goal-journey', detail: 'Travel or pilgrimage', category: 'travel' },
  { id: 'start_sadhana', label: 'Start a practice', icon: 'goal-lamp', detail: 'Vrat, japa or sadhana', category: 'travel' },
  { id: 'general', label: 'Something else', icon: 'goal-other', detail: 'Tell us what', category: 'other' },
];

const CATEGORIES: { id: MuhurtaCategory; label: string }[] = [
  { id: 'purchase', label: 'Buying' },
  { id: 'home', label: 'Home' },
  { id: 'family', label: 'Family' },
  { id: 'work', label: 'Work' },
  { id: 'travel', label: 'Travel & practice' },
  { id: 'other', label: 'Other' },
];

const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

const WHOSE_LABEL: Record<MuhurtaWhose, string> = {
  self: 'Timed to',
  child: 'Whose ceremony? Pick the child',
  couple: 'Timed to',
  family: 'Timed to (usually the head of the family)',
  mother: 'Timed to the mother-to-be',
};

/**
 * Muhurta — Choose a goal (Figma node 30:56).
 *
 * Electional astrology, asked the way people actually ask it: not "compute a
 * muhurta" but "I am taking delivery of a car, when is good". The goals are
 * the question in the reader's own words, grouped the way families plan them,
 * and each one carries the questions that change its answer: whose chart
 * (the baby's, both partners'), where it will happen, a day or night wedding,
 * which way a journey goes, and days the family avoids.
 *
 * "Something else" is not a fallback for a missing icon. Muhurta is asked about
 * things no fixed list will cover; the server maps typed words to the closest
 * goal's rules and says which it used.
 */
@Component({
  selector: 'as-muhurta-goal',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PlanLockComponent, BackLinkDirective, RouterLink, SelectHapticDirective, CityPickerComponent],
  templateUrl: './muhurta-goal.component.html',
  styleUrl: './muhurta-goal.component.scss',
})
export class MuhurtaGoalComponent {
  protected readonly gate = inject(PlanGateService);
  protected readonly locked = computed(() => !this.gate.allows('muhurta.full'));
  private readonly kundlis = inject(KundliStore);
  private readonly query = toSignal(inject(ActivatedRoute).queryParamMap, { requireSync: true });

  readonly goals = signal<MuhurtaGoal[]>(MUHURTA_GOALS);
  readonly categories = CATEGORIES;
  readonly weekdays = WEEKDAYS;

  private readonly preset = MUHURTA_GOALS.find((g) => g.id === this.query().get('goal'));
  readonly selectedGoal = signal<string>(this.preset?.id ?? 'buy_vehicle');
  readonly category = signal<MuhurtaCategory>(this.preset?.category ?? 'purchase');
  readonly visibleGoals = computed(() => this.goals().filter((g) => g.category === this.category()));
  readonly goal = computed(() => this.goals().find((g) => g.id === this.selectedGoal()) ?? null);

  readonly range = signal<MuhurtaRange>('month');
  readonly customFrom = signal(localIsoDate(new Date()));
  readonly customTo = signal(localIsoDate(addDays(new Date(), 14)));
  readonly fixedDate = signal(localIsoDate(new Date()));
  readonly customIntent = signal('');

  // ── The questions that change the answer ──
  readonly profiles = computed(() => this.kundlis.kundlis());
  readonly personId = signal<string | null>(null);
  readonly partnerId = signal<string | null>(null);
  readonly ceremony = signal<'' | 'day' | 'night'>('');
  readonly direction = signal<'' | 'north' | 'south' | 'east' | 'west'>('');
  readonly avoidDays = signal<string[]>([]);
  readonly observeSeason = signal(true);
  readonly showOptions = signal(false);
  readonly eventPlace = signal<PanchangaCity | null>(null);
  readonly choosingPlace = signal(false);

  readonly whose = computed<MuhurtaWhose>(() => this.goal()?.whose ?? 'self');
  readonly whoseLabel = computed(() => WHOSE_LABEL[this.whose()]);
  readonly effectivePersonId = computed(() => this.personId() ?? this.defaultPerson());
  private readonly defaultPerson = computed(() => {
    const list = this.profiles();
    if (this.whose() === 'child') {
      return list.find((k) => /child|son|daughter/i.test(k.relation))?.id ?? this.kundlis.activeId();
    }
    return this.kundlis.activeId();
  });
  readonly partnerOptions = computed(() => this.profiles().filter((k) => k.id !== this.effectivePersonId()));
  /** The other partner: chosen, else a spouse profile, else none (one chart only). */
  readonly effectivePartnerId = computed(() =>
    this.partnerId() ?? this.partnerOptions().find((k) => /spouse|wife|husband|partner|fianc/i.test(k.relation))?.id ?? null);

  /** Days ahead this plan may search (testers: 14), or null for no cap. */
  protected readonly horizon = computed(() => this.gate.limit('muhurta.days_ahead'));
  /** The last date a search may reach, as YYYY-MM-DD, or null. */
  protected readonly lastDate = computed(() => {
    const days = this.horizon();
    return days ? localIsoDate(addDays(new Date(), days - 1)) : null;
  });
  protected readonly today = localIsoDate(new Date());

  readonly ranges = computed<{ id: MuhurtaRange; label: string }[]>(() => [
    { id: 'week', label: 'This week' },
    this.horizon()
      ? { id: 'fortnight', label: horizonLabel(this.horizon()!) }
      : { id: 'month', label: 'This month' },
    { id: 'custom', label: 'Pick dates' },
    { id: 'date', label: 'One date' },
  ]);

  /**
   * Muhurta is local by definition — a window is sunrise-relative, so the same
   * instant is a different muhurta two cities apart. The event can be in
   * another city (a wedding in the hometown), so it can be set here without
   * moving the app-wide place.
   */
  private readonly preferences = inject(PreferencesService);
  readonly place = computed(() => {
    const event = this.eventPlace();
    if (event) {
      // From "Use my location" far from any known place: say so, since the
      // times are that place's, not the reader's.
      if ((event.distance_km ?? 0) > 30) {
        return `${event.city}, the nearest place we know (${Math.round(event.distance_km!)} km away)`;
      }
      return `${event.city}, where it will happen`;
    }
    // The sentence is written to stand alone; here it follows "Times for".
    return plannedTimingPlace(this.preferences.panchangaPlace(), this.preferences.browserTimezone()).sentence
      .replace(/^The /, 'the ');
  });

  // Nothing can be computed for a purpose that has not been chosen.
  protected readonly canSearch = computed(() => {
    if (!this.selectedGoal()) return false;
    if (this.selectedGoal() === 'general' && this.customIntent().trim().length < 3) return false;
    const last = this.lastDate();
    if (this.range() === 'date') return !!this.fixedDate() && (!last || this.fixedDate() <= last);
    if (this.range() !== 'custom') return true;
    const from = this.customFrom();
    const to = this.customTo();
    return !!from && !!to && from <= to && (!last || to <= last);
  });

  private readonly router = inject(Router);

  constructor() {
    void this.kundlis.load();
  }

  protected findWindows(): void {
    if (!this.canSearch()) {
      return;
    }
    const dates = this.selectedDates();
    const goal = this.goal();
    const place = this.eventPlace();
    const whose = this.whose();
    void this.router.navigate(['/m', 'muhurta', 'results'], {
      queryParams: {
        goal: this.selectedGoal(),
        intent: this.selectedGoal() === 'general' ? this.customIntent().trim() : null,
        range: this.range() === 'month' && this.horizon() ? 'fortnight' : this.range(),
        date_from: dates.from,
        date_to: dates.to,
        person: whose !== 'self' ? this.effectivePersonId() : null,
        partner: whose === 'couple' ? this.effectivePartnerId() : null,
        ceremony: this.selectedGoal() === 'marriage_related' && this.ceremony() ? this.ceremony() : null,
        direction: this.selectedGoal() === 'start_journey' && this.direction() ? this.direction() : null,
        avoid: this.avoidDays().length ? this.avoidDays().join(',') : null,
        season: goal?.season && !this.observeSeason() ? 'off' : null,
        city: place?.city ?? null,
        nation: place?.nation ?? null,
      },
    });
  }

  protected setCustomFrom(value: string): void {
    this.customFrom.set(value);
    if (this.customTo() < value) this.customTo.set(value);
  }

  protected setCustomTo(value: string): void {
    this.customTo.set(value);
  }

  protected selectCategory(id: MuhurtaCategory): void {
    this.category.set(id);
    const first = this.goals().find((g) => g.category === id);
    if (first && this.goal()?.category !== id) this.selectGoal(first.id);
  }

  protected selectGoal(goal: string): void {
    this.selectedGoal.set(goal);
    this.personId.set(null);
    this.partnerId.set(null);
    if (goal !== 'general') this.customIntent.set('');
  }

  protected toggleAvoid(day: string): void {
    this.avoidDays.update((days) => (days.includes(day) ? days.filter((d) => d !== day) : [...days, day]));
  }

  protected pickPlace(city: PanchangaCity): void {
    this.eventPlace.set(city);
    this.choosingPlace.set(false);
  }

  protected clearPlace(): void {
    this.eventPlace.set(null);
    this.choosingPlace.set(false);
  }

  protected profileLabel(id: string | null): string {
    return this.profiles().find((k) => k.id === id)?.name ?? '';
  }

  private selectedDates(): { from: string; to: string } {
    const today = new Date();
    if (this.range() === 'week') {
      return { from: localIsoDate(today), to: localIsoDate(addDays(today, 6)) };
    }
    if (this.range() === 'custom') {
      return { from: this.customFrom(), to: this.customTo() };
    }
    if (this.range() === 'date') {
      return { from: this.fixedDate(), to: this.fixedDate() };
    }
    const days = this.horizon();
    return { from: localIsoDate(today), to: localIsoDate(addDays(today, days ? days - 1 : 30)) };
  }
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

/**
 * YYYY-MM-DD in the phone's own calendar. `toISOString()` is UTC, so before
 * 05:30 in India it named yesterday and the search started a day early.
 */
export function localIsoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function horizonLabel(days: number): string {
  return days % 7 === 0 ? `Next ${days / 7} weeks` : `Next ${days} days`;
}
