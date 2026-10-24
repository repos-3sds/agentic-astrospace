import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';

import { SIGN_ORDER, signMeta } from '../../core/glyphs';
import { currentTextZoom } from '../../core/text-zoom';
import { PlanetConditionAnnotation, PlanetConditionCode, VargaChart } from '../../core/models';
import {
  Box,
  estimateText,
  fitRegion,
  FitOptions,
  FitRegion,
  labelBox,
  MeasureText,
  Point,
} from './kundli-chart-layout';

export type KundliChartStyle = 'north' | 'south' | 'eastern';

interface PlanetEntry {
  key: string;
  label: string;
  annotations: PlanetConditionAnnotation[];
}

/** A fixed label: house number or sign. */
interface ChartLabel {
  text: string;
  cls: 'house-number' | 'sign-label';
  x: number;
  y: number;
  /** Font size to write, in chart units (before the phone's text zoom). */
  size: number;
  anchor: 'start' | 'middle' | 'end';
  fill: string | null;
}

interface PlacedEntry {
  entry: PlanetEntry;
  x: number;
  y: number;
  size: number;
  symbolSize: number;
  hit: Box;
}

interface ChartRegion {
  key: string;
  labels: ChartLabel[];
  entries: PlacedEntry[];
}

/**
 * Type sizes in chart units (the SVG is 400 wide, drawn about 316-350 px on a
 * phone, so 15.5 units is about 12-13.5 px). Tester feedback 2026-10-20: the
 * old 10-11 units read at 8-9 px and were too small to read inside the chart.
 * Planets shrink toward PLANET_MIN only in a house too crowded to hold them.
 */
const HOUSE_SIZE = 12.5;
const SIGN_SIZE = 14;
const EASTERN_SIGN_SIZE = 13.5;
const PLANET_MAX = 15.5;
const PLANET_MIN = 10;
/** Only for a stellium in a small house; smaller type beats text across the lines. */
const PLANET_FLOOR = 8;
const SYMBOL_RATIO = 0.82;
const SYMBOL_GAP = 3;

/**
 * Tap targets for the planet labels, in chart units (54 units is about 45 px
 * on a phone). Flow audit 2026-10-15, section 6: they were 37 x 12 px.
 *
 * Each target stays centred on its own label, so a tap on a label always
 * lands on that planet. Rows of a stack abut at the row spacing; the stack's
 * first and last rows grow outward until the stack is 54 units tall, so a lone
 * planet is a full 44 px target. Side by side columns split the width.
 */
const HIT = 54;

const A = 133.33;
const B = 266.67;

interface NorthHouse {
  house: number;
  poly: Point[];
  anchor: Point;
}

/** North diamond: frame 20-380, centre 200; houses run anticlockwise from the top diamond. */
const NORTH_HOUSES: NorthHouse[] = [
  { house: 1, poly: [[200, 20], [290, 110], [200, 200], [110, 110]], anchor: [200, 104] },
  { house: 2, poly: [[20, 20], [200, 20], [110, 110]], anchor: [110, 54] },
  { house: 3, poly: [[20, 20], [110, 110], [20, 200]], anchor: [56, 110] },
  { house: 4, poly: [[20, 200], [110, 110], [200, 200], [110, 290]], anchor: [104, 200] },
  { house: 5, poly: [[20, 200], [110, 290], [20, 380]], anchor: [56, 290] },
  { house: 6, poly: [[20, 380], [110, 290], [200, 380]], anchor: [110, 344] },
  { house: 7, poly: [[200, 380], [110, 290], [200, 200], [290, 290]], anchor: [200, 296] },
  { house: 8, poly: [[200, 380], [290, 290], [380, 380]], anchor: [290, 344] },
  { house: 9, poly: [[380, 380], [290, 290], [380, 200]], anchor: [344, 290] },
  { house: 10, poly: [[380, 200], [290, 290], [200, 200], [290, 110]], anchor: [296, 200] },
  { house: 11, poly: [[380, 200], [290, 110], [380, 20]], anchor: [344, 110] },
  { house: 12, poly: [[380, 20], [290, 110], [200, 20]], anchor: [290, 54] },
];

const SOUTH_SIGN_POINTS: Record<string, { col: number; row: number }> = {
  Pisces: { col: 0, row: 0 },
  Aries: { col: 1, row: 0 },
  Taurus: { col: 2, row: 0 },
  Gemini: { col: 3, row: 0 },
  Aquarius: { col: 0, row: 1 },
  Cancer: { col: 3, row: 1 },
  Capricorn: { col: 0, row: 2 },
  Leo: { col: 3, row: 2 },
  Sagittarius: { col: 0, row: 3 },
  Scorpio: { col: 1, row: 3 },
  Libra: { col: 2, row: 3 },
  Virgo: { col: 3, row: 3 },
};

/**
 * Eastern chart geometry. Grid: 400×400, thirds at 133.33/266.67; corner
 * cells split by diagonals through the outer corners (TL/BR on x=y-style
 * lines, TR/BL on x+y=400-style lines).
 *
 * Zones are keyed by the sign that sits there in the classic Bengali/Odia
 * chart: Aries (Mesha) fixed in the top middle box, the rest anticlockwise.
 * Signs never move; the Lagna's box is marked "As" and each box carries its
 * house number. Hawk asked for this on 2026-10-24, replacing the Lagna-top
 * variant of 2026-10-20 (and before that, Taurus on top running clockwise).
 *
 * Per zone: `poly` is the zone's outline and `anchor` where its planets sit
 * when there is room; (labelX, labelY) pins the house number and sign number into
 * the zone's outer pocket, inside the viewBox so nothing clips.
 */
const EASTERN_ZONES: Record<string, {
  poly: Point[];
  anchor: Point;
  labelX: number;
  labelY: number;
  labelAlign: 'start' | 'middle' | 'end';
}> = {
  // Top edge.
  Aries: { poly: [[A, 0], [B, 0], [B, A], [A, A]], anchor: [200, 76], labelX: 140, labelY: 16, labelAlign: 'start' },
  // Top-left corner: Taurus upper-right triangle, Gemini lower-left.
  Taurus: { poly: [[0, 0], [A, 0], [A, A]], anchor: [96, 56], labelX: 126, labelY: 16, labelAlign: 'end' },
  Gemini: { poly: [[0, 0], [A, A], [0, A]], anchor: [38, 82], labelX: 8, labelY: 104, labelAlign: 'start' },
  // Left edge.
  Cancer: { poly: [[0, A], [A, A], [A, B], [0, B]], anchor: [76, 212], labelX: 8, labelY: 149, labelAlign: 'start' },
  // Bottom-left corner: Leo upper-left triangle, Virgo lower-right.
  Leo: { poly: [[0, B], [A, B], [0, 400]], anchor: [38, 318], labelX: 8, labelY: 282, labelAlign: 'start' },
  Virgo: { poly: [[A, B], [A, 400], [0, 400]], anchor: [96, 344], labelX: 126, labelY: 366, labelAlign: 'end' },
  // Bottom edge.
  Libra: { poly: [[A, B], [B, B], [B, 400], [A, 400]], anchor: [212, 318], labelX: 140, labelY: 358, labelAlign: 'start' },
  // Bottom-right corner: Scorpio lower-left triangle, Sagittarius upper-right.
  Scorpio: { poly: [[B, B], [400, 400], [B, 400]], anchor: [304, 344], labelX: 274, labelY: 366, labelAlign: 'start' },
  Sagittarius: { poly: [[B, B], [400, B], [400, 400]], anchor: [362, 318], labelX: 392, labelY: 282, labelAlign: 'end' },
  // Right edge.
  Capricorn: { poly: [[B, A], [400, A], [400, B], [B, B]], anchor: [324, 212], labelX: 392, labelY: 149, labelAlign: 'end' },
  // Top-right corner: Aquarius lower-right triangle, Pisces upper-left.
  Aquarius: { poly: [[400, 0], [400, A], [B, A]], anchor: [362, 82], labelX: 392, labelY: 104, labelAlign: 'end' },
  Pisces: { poly: [[B, 0], [400, 0], [B, A]], anchor: [304, 56], labelX: 274, labelY: 16, labelAlign: 'start' },
};

@Component({
  // Signal inputs only, so OnPush is safe; the mobile chart screens render these (audit I16).
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-kundli-chart',
  templateUrl: './kundli-chart.component.html',
  styleUrl: './kundli-chart.component.scss',
})
export class KundliChartComponent {
  readonly chart = input<VargaChart | null>(null);
  readonly chartStyle = input<KundliChartStyle>('north');
  readonly annotations = input<Record<string, PlanetConditionAnnotation[]>>({});
  readonly interactive = input(false);
  readonly planetSelected = output<string>();

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  /** Bumped when web fonts finish loading, so widths are measured again. */
  private readonly fontsReady = signal(0);
  private readonly zoom = signal(1);
  private readonly widthCache = new Map<string, number>();
  private context: CanvasRenderingContext2D | null = null;

  constructor() {
    afterNextRender(() => {
      // The WebView's text zoom (core/text-zoom.ts), SVG text included.
      this.zoom.set(currentTextZoom());
      this.fontsReady.update((n) => n + 1);
      document.fonts?.ready.then(() => {
        this.widthCache.clear();
        this.fontsReady.update((n) => n + 1);
      });
    });
  }

  protected selectPlanet(entry: PlanetEntry): void {
    if (this.interactive()) this.planetSelected.emit(entry.key);
  }

  protected readonly regions = computed<ChartRegion[]>(() => {
    const chart = this.chart();
    if (!chart) return [];
    this.fontsReady();
    const zoom = this.zoom();
    const measure = this.measurer();
    const style = this.chartStyle();
    if (style === 'north') return this.northRegions(chart, zoom, measure);
    if (style === 'eastern') return this.easternRegions(chart, zoom, measure);
    return this.southRegions(chart, zoom, measure);
  });

  private options(zoom: number): FitOptions {
    return {
      maxSize: PLANET_MAX * zoom,
      // A crowded house never drops below today's size at normal text, so a
      // large-text reader keeps a little of their zoom there too.
      minSize: Math.min(PLANET_MAX, PLANET_MIN * zoom),
      floorSize: PLANET_FLOOR,
      symbolRatio: SYMBOL_RATIO,
      symbolGap: SYMBOL_GAP,
      margin: 3,
    };
  }

  private northRegions(chart: VargaChart, zoom: number, measure: MeasureText): ChartRegion[] {
    const byHouse = new Map<number, PlanetEntry[]>();
    for (const [planet, position] of Object.entries(chart.planets)) {
      byHouse.set(position.house, [...(byHouse.get(position.house) ?? []), this.entryForPlanet(planet)]);
    }
    const lagnaIndex = SIGN_ORDER.indexOf(chart.lagna.sign);
    const options = this.options(zoom);
    return NORTH_HOUSES.map((house) => {
      const sign = this.signForHouse(lagnaIndex, chart.lagna.sign, house.house);
      const entries = house.house === 1
        ? [this.lagnaEntry(), ...(byHouse.get(house.house) ?? [])]
        : (byHouse.get(house.house) ?? []);
      const houseText = `H${house.house}`;
      // North houses are fixed and the signs move with the lagna, so each
      // house says which sign it holds: its number, as printed North charts
      // write it (1 Aries ... 12 Pisces).
      const signText = String(SIGN_ORDER.indexOf(sign) + 1);
      const region: FitRegion = {
        poly: house.poly,
        anchor: house.anchor,
        header: [
          { text: houseText, size: HOUSE_SIZE * zoom, kind: 'label' },
          { text: signText, size: SIGN_SIZE * zoom, kind: 'sign' },
        ],
        entries: entries.map((entry) => this.fitEntry(entry)),
      };
      const fit = fitRegion(region, measure, options);
      return {
        key: `n${house.house}`,
        labels: [
          { text: houseText, cls: 'house-number', x: fit.header[0].x, y: fit.header[0].y, size: fit.header[0].size / zoom, anchor: 'middle', fill: null },
          { text: signText, cls: 'sign-label', x: fit.header[1].x, y: fit.header[1].y, size: fit.header[1].size / zoom, anchor: 'middle', fill: signMeta(sign).color },
        ],
        entries: this.placeEntries(entries, fit, zoom),
      };
    });
  }

  private southRegions(chart: VargaChart, zoom: number, measure: MeasureText): ChartRegion[] {
    const bySign = this.planetsBySign(chart);
    const lagnaIndex = SIGN_ORDER.indexOf(chart.lagna.sign);
    const options = this.options(zoom);
    return SIGN_ORDER.map((sign) => {
      const point = SOUTH_SIGN_POINTS[sign];
      const x0 = point.col * 100;
      const y0 = point.row * 100;
      const entries = sign === chart.lagna.sign
        ? [this.lagnaEntry(), ...(bySign.get(sign) ?? [])]
        : (bySign.get(sign) ?? []);
      const houseText = `H${this.houseForSign(lagnaIndex, sign)}`;
      // South signs never move, so a cell's place names its sign; only the
      // house number is written, top-left, 8 units in.
      const houseY = y0 + 8 + HOUSE_SIZE * zoom * 0.6;
      const houseBox = labelBox(x0 + 8, houseY, measure(houseText, HOUSE_SIZE * zoom, 'label'), HOUSE_SIZE * zoom, 'start');
      const fit = fitRegion({
        poly: [[x0, y0], [x0 + 100, y0], [x0 + 100, y0 + 100], [x0, y0 + 100]],
        anchor: [x0 + 50, y0 + 48],
        exclude: [houseBox],
        entries: entries.map((entry) => this.fitEntry(entry)),
      }, measure, options);
      return {
        key: `s${sign}`,
        labels: [
          { text: houseText, cls: 'house-number', x: x0 + 8, y: houseY, size: HOUSE_SIZE, anchor: 'start', fill: null },
        ],
        entries: this.placeEntries(entries, fit, zoom),
      };
    });
  }

  private easternRegions(chart: VargaChart, zoom: number, measure: MeasureText): ChartRegion[] {
    const bySign = this.planetsBySign(chart);
    const lagnaIndex = SIGN_ORDER.indexOf(chart.lagna.sign);
    const options = this.options(zoom);
    const houseSize = HOUSE_SIZE * zoom;
    return SIGN_ORDER.map((sign) => {
      const house = this.houseForSign(lagnaIndex, sign);
      const zone = EASTERN_ZONES[sign];
      const entries = sign === chart.lagna.sign
        ? [this.lagnaEntry('As'), ...(bySign.get(sign) ?? [])]
        : (bySign.get(sign) ?? []);
      const houseText = `H${house}`;
      // Each box also names its sign by number under the house number, in the
      // sign's colour, as the North chart does.
      const signText = String(SIGN_ORDER.indexOf(sign) + 1);
      const signSize = EASTERN_SIGN_SIZE * zoom;
      const spacing = Math.max(houseSize, signSize) * 1.15;
      // Keep the two-line label inside the frame however large the text is.
      const houseY = Math.min(Math.max(zone.labelY, 4 + houseSize * 0.6), 396 - spacing - signSize * 0.6);
      const signY = houseY + spacing;
      const exclude = [
        labelBox(zone.labelX, houseY, measure(houseText, houseSize, 'label'), houseSize, zone.labelAlign),
        labelBox(zone.labelX, signY, measure(signText, signSize, 'sign'), signSize, zone.labelAlign),
      ];
      const fit = fitRegion({
        poly: zone.poly,
        anchor: zone.anchor,
        exclude,
        entries: entries.map((entry) => this.fitEntry(entry)),
      }, measure, options);
      return {
        key: `e${sign}`,
        labels: [
          { text: houseText, cls: 'house-number', x: zone.labelX, y: houseY, size: HOUSE_SIZE, anchor: zone.labelAlign, fill: null },
          { text: signText, cls: 'sign-label', x: zone.labelX, y: signY, size: EASTERN_SIGN_SIZE, anchor: zone.labelAlign, fill: signMeta(sign).color },
        ],
        entries: this.placeEntries(entries, fit, zoom),
      };
    });
  }

  private fitEntry(entry: PlanetEntry) {
    return { label: entry.label, symbols: entry.annotations.map((annotation) => annotation.symbol) };
  }

  /** Turns a fit (rendered sizes) into what to write (sizes before text zoom) plus tap targets. */
  private placeEntries(entries: PlanetEntry[], fit: ReturnType<typeof fitRegion>, zoom: number): PlacedEntry[] {
    const extra = Math.max(0, HIT - fit.rowHeight * fit.rows) / 2;
    const width = fit.columns === 1 ? HIT : Math.min(HIT, fit.columnPitch);
    return entries.map((entry, i) => {
      const placed = fit.entries[i];
      const row = Math.floor(i / fit.columns);
      let y = placed.y - fit.rowHeight / 2;
      let h = fit.rowHeight;
      if (row === 0) { y -= extra; h += extra; }
      if (row === fit.rows - 1) h += extra;
      return {
        entry,
        x: placed.x,
        y: placed.y,
        size: placed.size / zoom,
        symbolSize: (placed.size * SYMBOL_RATIO) / zoom,
        hit: { x: placed.x - width / 2, y, w: width, h },
      };
    });
  }

  /** Text widths from the fonts actually in use, falling back to estimates. */
  private measurer(): MeasureText {
    if (!this.context && typeof document !== 'undefined') {
      try {
        this.context = document.createElement('canvas').getContext('2d');
      } catch {
        this.context = null;
      }
    }
    const context = this.context;
    if (!context || typeof getComputedStyle === 'undefined') return estimateText;
    const styles = getComputedStyle(this.host.nativeElement);
    const body = styles.fontFamily || 'sans-serif';
    const display = styles.getPropertyValue('--as-font-display').trim() || body;
    const fonts = {
      planet: `650 100px ${body}`,
      symbol: `900 100px ${body}`,
      label: `700 100px ${body}`,
      sign: `700 100px ${display}`,
    };
    return (text, size, kind) => {
      const key = `${kind}|${text}`;
      let width = this.widthCache.get(key);
      if (width === undefined) {
        context.font = fonts[kind];
        width = context.measureText(text).width;
        // House numbers are tracked out 0.08em per letter.
        if (kind === 'label') width += [...text].length * 8;
        this.widthCache.set(key, width);
      }
      return (width * size) / 100;
    };
  }

  private planetsBySign(chart: VargaChart): Map<string, PlanetEntry[]> {
    const planetsBySign = new Map<string, PlanetEntry[]>();
    for (const [planet, position] of Object.entries(chart.planets)) {
      planetsBySign.set(position.sign, [...(planetsBySign.get(position.sign) ?? []), this.entryForPlanet(planet)]);
    }
    return planetsBySign;
  }

  private signForHouse(lagnaIndex: number, fallback: string, house: number): string {
    if (lagnaIndex < 0) return fallback;
    return SIGN_ORDER[(lagnaIndex + house - 1) % SIGN_ORDER.length];
  }

  private houseForSign(lagnaIndex: number, sign: string): number {
    const signIndex = SIGN_ORDER.indexOf(sign);
    if (lagnaIndex < 0 || signIndex < 0) return 0;
    return ((signIndex - lagnaIndex + SIGN_ORDER.length) % SIGN_ORDER.length) + 1;
  }

  private planetShortName(planet: string): string {
    const names: Record<string, string> = {
      Sun: 'Su',
      Moon: 'Mo',
      Mercury: 'Me',
      Venus: 'Ve',
      Mars: 'Ma',
      Jupiter: 'Ju',
      Saturn: 'Sa',
      Rahu: 'Ra',
      Ketu: 'Ke',
      Uranus: 'Ur',
      Neptune: 'Ne',
      Pluto: 'Pl',
    };
    return names[planet] ?? planet.slice(0, 2);
  }

  private entryForPlanet(planet: string): PlanetEntry {
    const chartPlanet = this.chart()?.planets[planet];
    const automatic: PlanetConditionAnnotation[] = [];
    if (chartPlanet?.retrograde) {
      automatic.push({ code: 'retrograde', symbol: '↺', label: 'Retrograde', tone: 'neutral' });
    }
    if (chartPlanet?.vargottama) {
      automatic.push({ code: 'vargottama', symbol: '✦', label: 'Vargottama', tone: 'good' });
    }
    return {
      key: planet,
      label: this.planetShortName(planet),
      annotations: this.mergeAnnotations(automatic, this.annotations()[planet] ?? []),
    };
  }

  private lagnaEntry(label = 'Lagna'): PlanetEntry {
    return { key: 'Lagna', label, annotations: [] };
  }

  private mergeAnnotations(
    first: PlanetConditionAnnotation[],
    second: PlanetConditionAnnotation[],
  ): PlanetConditionAnnotation[] {
    const seen = new Set<PlanetConditionCode>();
    return [...first, ...second].filter((item) => {
      if (seen.has(item.code)) return false;
      seen.add(item.code);
      return true;
    });
  }
}
