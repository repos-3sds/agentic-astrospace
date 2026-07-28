import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ChartCell, EastChartComponent, PlanetSelection } from './east-chart.component';
import { PlanetDetail, PlanetSheetComponent } from './planet-sheet.component';
import { RegionalChartComponent } from './regional-chart.component';

/** The three drawing conventions the app can render a chart in. */
export type ChartStyle = 'Eastern' | 'South' | 'North';

/** Readings for the tappable placements, keyed by each individual glyph. */
const PLACEMENTS: Record<string, PlanetDetail> = {
  Su: {
    abbr: 'Su',
    title: 'Sun in Gemini',
    position: '23° 14’ · 3rd house',
    house: '3rd house',
    reading:
      'Your Sun sits in Gemini in the 3rd house — a curious, communicative core self that thinks by talking things through. This placement leans toward courage in small, steady steps rather than one big leap.',
  },
  Me: {
    abbr: 'Me',
    title: 'Mercury in Gemini',
    position: '18° 42’ · 3rd house',
    house: '3rd house',
    reading:
      'Mercury is in its own sign in Gemini in the 3rd house. This supports quick pattern recognition, flexible language and a mind that learns by comparing several viewpoints.',
  },
  Ve: {
    abbr: 'Ve',
    title: 'Venus with the Ascendant',
    position: '11° 02’ · 1st house',
    house: '1st house',
    reading:
      'Venus sits with your rising sign, which tends to soften first impressions — people usually read you as approachable before they read you as anything else.',
  },
  As: {
    abbr: 'As',
    title: 'Ascendant in Taurus',
    position: '08° 36’ · 1st house',
    house: '1st house',
    reading:
      'Taurus rising gives the chart a steady, embodied approach. You tend to trust what proves durable in practice and prefer changes that can be integrated at a measured pace.',
  },
  Mo: {
    abbr: 'Mo',
    title: 'Moon in Cancer',
    position: '04° 51’ · 4th house',
    house: '4th house',
    reading:
      'The Moon is at home in Cancer in the 4th — feelings run close to the surface around family and home, and that is a strength here rather than a fragility.',
  },
  Ma: {
    abbr: 'Ma',
    title: 'Mars in Scorpio',
    position: '18° 33’ · 7th house',
    house: '7th house',
    reading:
      'Mars in its own sign in the 7th brings force to partnerships — useful when something needs settling, worth watching when it does not.',
  },
  Sa: {
    abbr: 'Sa',
    title: 'Saturn in Virgo',
    position: '26° 09’ · 5th house',
    house: '5th house',
    reading:
      'Saturn in Virgo asks for patience with the things you make. Progress here is slow and then durable, which is the trade Saturn usually offers.',
  },
  Ju: {
    abbr: 'Ju',
    title: 'Jupiter in Capricorn',
    position: '02° 47’ · 9th house',
    house: '9th house',
    reading:
      'Jupiter is in its fall in Capricorn, but in the 9th — the house it rules by nature. Expect growth that arrives through discipline rather than luck.',
  },
  Ra: {
    abbr: 'Ra',
    title: 'Rahu in Sagittarius',
    position: '14° 21’ · 8th house',
    house: '8th house',
    reading:
      'Rahu in the 8th points appetite toward what is hidden — research, inheritance, the things other people avoid discussing.',
  },
  Ke: {
    abbr: 'Ke',
    title: 'Ketu in Pisces',
    position: '14° 21’ · 2nd house',
    house: '2nd house',
    reading:
      'Ketu in the 2nd loosens attachment to accumulation. Money tends to matter to you instrumentally rather than as a scoreboard.',
  },
};

/**
 * Chart — full render (Figma node 36:86).
 *
 * Step two of the chart flow. The style toggle is the point of the screen: the
 * same chart drawn Eastern, South or North is three different-looking diagrams,
 * and which one a reader recognises depends entirely on where they learned. The
 * app should not decide that for them.
 *
 * Only occupied houses are tappable. An empty house has nothing to say, and a
 * sheet that opened to explain nothing would teach people that tapping is not
 * worth it.
 */
@Component({
  selector: 'as-chart-full',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EastChartComponent, PlanetSheetComponent, RegionalChartComponent, RouterLink],
  templateUrl: './chart-full.component.html',
  styleUrl: './chart-full.component.scss',
})
export class ChartFullComponent {
  readonly styles: ChartStyle[] = ['Eastern', 'South', 'North'];
  readonly style = signal<ChartStyle>('Eastern');

  /**
   * Placements as percentages of the 337px frame, from the design's own
   * coordinates (node 44:96). Percentages rather than pixels so the same data
   * drives the hub's 160px preview.
   */
  readonly cells = signal<ChartCell[]>([
    { sign: 'Ta', planets: 'As · Ve', x: 44.5, y: 9.4 },
    { sign: 'Ge', planets: 'Su · Me', x: 70.9, y: 5.4 },
    { sign: 'Cn', planets: 'Mo', x: 87.5, y: 20.4 },
    { sign: 'Le', x: 84.2, y: 47.9 },
    { sign: 'Vi', planets: 'Sa', x: 89.6, y: 71.4 },
    { sign: 'Li', x: 74.7, y: 88.6 },
    { sign: 'Sc', planets: 'Ma', x: 47.5, y: 81.4 },
    { sign: 'Sg', planets: 'Ra', x: 21.3, y: 87.1 },
    { sign: 'Cp', planets: 'Ju', x: 7.9, y: 72.1 },
    { sign: 'Aq', x: 11.9, y: 47.9 },
    { sign: 'Pi', planets: 'Ke', x: 20.6, y: 6.1 },
    { sign: 'Ar', x: 8.4, y: 21.9 },
  ]);

  /** Expanded once, so the legend is not a second thing to decode. */
  readonly legend = [
    { abbr: 'As', name: 'Ascendant' },
    { abbr: 'Su', name: 'Sun' },
    { abbr: 'Mo', name: 'Moon' },
    { abbr: 'Ma', name: 'Mars' },
    { abbr: 'Me', name: 'Mercury' },
    { abbr: 'Ju', name: 'Jupiter' },
    { abbr: 'Ve', name: 'Venus' },
    { abbr: 'Sa', name: 'Saturn' },
    { abbr: 'Ra', name: 'Rahu' },
    { abbr: 'Ke', name: 'Ketu' },
  ];

  readonly selected = signal<PlanetDetail | null>(null);

  protected openPlanet(selection: PlanetSelection): void {
    const detail = PLACEMENTS[selection.planet];
    if (detail) {
      this.selected.set(detail);
    }
  }
}
