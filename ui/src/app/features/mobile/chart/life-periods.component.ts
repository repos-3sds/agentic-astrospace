import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { PreferencesService } from '../../../core/preferences.service';

interface Period {
  name: string;
  dates: string;
  active?: boolean;
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
  protected readonly preferences = inject(PreferencesService);

  readonly system = signal<'vimshottari' | 'yogini'>('vimshottari');
  readonly level = signal<'maha' | 'antar' | 'pratyantar'>('antar');

  readonly antarPeriods: Period[] = [
    { name: 'Venus – Venus', dates: '2013–2016' },
    { name: 'Venus – Sun', dates: '2016–2017' },
    { name: 'Venus – Moon', dates: '2017–2019' },
    { name: 'Venus – Mars', dates: '2019–2020' },
    { name: 'Venus – Rahu', dates: '2020–2023' },
    { name: 'Venus – Jupiter', dates: '2023–2025' },
    { name: 'Venus – Saturn', dates: '2025–2028', active: true },
    { name: 'Venus – Mercury', dates: '2028–2031' },
    { name: 'Venus – Ketu', dates: '2031–2033' },
  ];

  readonly mahaPeriods: Period[] = [
    { name: 'Ketu', dates: '2006–2013' },
    { name: 'Venus', dates: '2013–2033', active: true },
    { name: 'Sun', dates: '2033–2039' },
    { name: 'Moon', dates: '2039–2049' },
    { name: 'Mars', dates: '2049–2056' },
    { name: 'Rahu', dates: '2056–2074' },
    { name: 'Jupiter', dates: '2074–2090' },
    { name: 'Saturn', dates: '2090–2109' },
    { name: 'Mercury', dates: '2109–2126' },
  ];

  readonly pratyantarPeriods: Period[] = [
    { name: 'Saturn – Saturn', dates: 'Jan–Jun 2025' },
    { name: 'Saturn – Mercury', dates: 'Jun–Nov 2025' },
    { name: 'Saturn – Ketu', dates: 'Nov 2025–Jan 2026' },
    { name: 'Saturn – Venus', dates: 'Jan–Jul 2026', active: true },
    { name: 'Saturn – Sun', dates: 'Jul–Sep 2026' },
    { name: 'Saturn – Moon', dates: 'Sep–Dec 2026' },
    { name: 'Saturn – Mars', dates: 'Dec 2026–Feb 2027' },
    { name: 'Saturn – Rahu', dates: 'Feb–Jul 2027' },
    { name: 'Saturn – Jupiter', dates: 'Jul–Dec 2027' },
  ];

  readonly yoginiPeriods: Period[] = [
    { name: 'Mangala', dates: '1991–1992' },
    { name: 'Pingala', dates: '1992–1994' },
    { name: 'Dhanya', dates: '1994–1997' },
    { name: 'Bhramari', dates: '1997–2001' },
    { name: 'Bhadrika', dates: '2001–2006' },
    { name: 'Ulka', dates: '2006–2012' },
    { name: 'Siddha', dates: '2012–2019' },
    { name: 'Sankata', dates: '2019–2027', active: true },
  ];

  readonly periods = computed(() => {
    if (this.system() === 'yogini') return this.yoginiPeriods;
    if (this.level() === 'maha') return this.mahaPeriods;
    if (this.level() === 'pratyantar') return this.pratyantarPeriods;
    return this.antarPeriods;
  });

  protected chooseSystem(system: 'vimshottari' | 'yogini'): void {
    this.system.set(system);
    this.resetScroll();
  }

  protected chooseLevel(level: 'maha' | 'antar' | 'pratyantar'): void {
    this.system.set('vimshottari');
    this.level.set(level);
    this.resetScroll();
  }

  protected drill(period: Period): void {
    if (this.system() === 'yogini') return;
    if (this.level() === 'maha' && period.name === 'Venus') this.level.set('antar');
    else if (this.level() === 'antar' && period.name === 'Venus – Saturn') {
      this.level.set('pratyantar');
    }
    this.resetScroll();
  }

  private resetScroll(): void {
    requestAnimationFrame(() => this.host.nativeElement.scrollIntoView({ block: 'start' }));
  }
}
