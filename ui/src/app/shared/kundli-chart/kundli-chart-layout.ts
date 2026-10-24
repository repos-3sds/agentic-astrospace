/**
 * Fits the writing inside each house of a kundli chart.
 *
 * Every house is a convex shape on the 400-unit chart: the North diamond's
 * rhombi and triangles, the South grid's squares, the Eastern grid's squares
 * and half-squares. A house's text is a block of rows (an optional header,
 * then the planets), and this module finds the largest type size, the fewest
 * columns and the position nearest the house's natural centre at which every
 * row sits inside the shape and clear of the fixed labels.
 *
 * Before this, sizes were fixed and a stellium simply ran out of its house:
 * eight planets in a North corner triangle spilled across two lines of the
 * diagram. A crowded house now goes to two or three columns and, only if it
 * must, to smaller type; a quiet house keeps the full size.
 *
 * Sizes are in chart units as RENDERED, so they include the phone's text zoom
 * (Android scales WebView text, SVG text included, up to 102%). The caller
 * divides by the zoom before writing font sizes, so the text the WebView draws
 * is the text that was fitted.
 */

export type Point = readonly [number, number];

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Width of `text` at `size` chart units. */
export type MeasureText = (text: string, size: number, kind: 'planet' | 'symbol' | 'label' | 'sign') => number;

export interface FitEntry {
  label: string;
  symbols: string[];
}

export interface FitHeaderLine {
  text: string;
  size: number;
  kind: 'label' | 'sign';
}

export interface FitRegion {
  /** Convex house outline, in order. */
  poly: readonly Point[];
  /** Where the block would sit with room to spare: its centre. */
  anchor: Point;
  /** Fixed writing in the house the block must not touch. */
  exclude?: Box[];
  /** Lines stacked above the planets (North: house number and sign). */
  header?: FitHeaderLine[];
  /** Set once the header has been shrunk to make room. */
  headerShrunk?: boolean;
  entries: FitEntry[];
}

export interface FitOptions {
  maxSize: number;
  minSize: number;
  /** Last resort for a house that cannot hold its planets at minSize. */
  floorSize: number;
  /** Symbol size as a share of the planet size. */
  symbolRatio: number;
  /** Space between a planet and each of its symbols, in chart units. */
  symbolGap: number;
  /** Clearance from the house's lines. */
  margin: number;
}

export interface PlacedText {
  x: number;
  y: number;
  size: number;
}

export interface FitResult {
  size: number;
  columns: number;
  header: PlacedText[];
  /** Centre of each entry's text, in input order. */
  entries: PlacedText[];
  rowHeight: number;
  columnPitch: number;
  rows: number;
  /** False when nothing fitted even at the smallest size and the best effort was used. */
  fitted: boolean;
}

const LINE = 1.2;
const HEADER_LINE = 1.22;
const HEADER_GAP = 2;

export function entryWidth(entry: FitEntry, size: number, measure: MeasureText, options: FitOptions): number {
  let width = measure(entry.label, size, 'planet');
  for (const symbol of entry.symbols) {
    width += options.symbolGap + measure(symbol, size * options.symbolRatio, 'symbol');
  }
  return width;
}

interface Edge {
  /** Inside means k·x ≥ c0 + cy·y, with the margin already folded into c0. */
  k: number;
  c0: number;
  cy: number;
}

/** Each edge of a convex polygon as a half-plane, pulled in by `m`. */
function edgesOf(poly: readonly Point[], m: number): Edge[] {
  let area = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % poly.length];
    area += x1 * y2 - x2 * y1;
  }
  const sign = area > 0 ? 1 : -1;
  return poly.map(([x1, y1], i) => {
    const [x2, y2] = poly[(i + 1) % poly.length];
    const ex = x2 - x1;
    const ey = y2 - y1;
    const len = Math.hypot(ex, ey) || 1;
    // sign·(ex·(y − y1) − ey·(x − x1)) ≥ m·len, solved for x.
    return { k: -ey * sign, c0: m * len + sign * (ex * y1 - ey * x1), cy: -sign * ex };
  });
}

/** The x range inside the polygon at height y, or null when y is outside it. */
function spanAt(edges: Edge[], y: number): [number, number] | null {
  let left = -Infinity;
  let right = Infinity;
  for (const edge of edges) {
    const rhs = edge.c0 + edge.cy * y;
    if (Math.abs(edge.k) < 1e-9) {
      if (rhs > 1e-9) return null;
    } else if (edge.k > 0) {
      left = Math.max(left, rhs / edge.k);
    } else {
      right = Math.min(right, rhs / edge.k);
    }
  }
  return left <= right ? [left, right] : null;
}

/**
 * The centre nearest `want` at which a row `w` wide spanning y0..y1 sits
 * inside the polygon and clear of the excluded boxes, or null if none lies
 * within `reach`. A convex shape holds a box exactly when it holds the box's
 * corners, so the top and bottom spans decide it.
 */
function rowCentre(edges: Edge[], exclude: Box[], m: number, y0: number, y1: number, w: number, want: number, reach: number): number | null {
  const top = spanAt(edges, y0);
  const bottom = spanAt(edges, y1);
  if (!top || !bottom) return null;
  let allowed: [number, number][] = [[Math.max(top[0], bottom[0]) + w / 2, Math.min(top[1], bottom[1]) - w / 2]];
  for (const box of exclude) {
    if (y1 <= box.y - m || y0 >= box.y + box.h + m) continue;
    const lo = box.x - m - w / 2;
    const hi = box.x + box.w + m + w / 2;
    allowed = allowed.flatMap(([a, b]): [number, number][] => [[a, Math.min(b, lo)], [Math.max(a, hi), b]]);
  }
  let best: number | null = null;
  for (const [a, b] of allowed) {
    if (a > b) continue;
    const c = Math.min(Math.max(want, a), b);
    if (Math.abs(c - want) <= reach && (best === null || Math.abs(c - want) < Math.abs(best - want))) best = c;
  }
  return best;
}

interface Candidate {
  size: number;
  columns: number;
  headerLast: boolean;
  score: number;
}

interface BlockShape {
  height: number;
  /** Row boxes relative to the block's top centre. */
  rows: Box[];
  header: { dy: number; size: number }[];
  entries: { dx: number; dy: number; row: number }[];
  rowHeight: number;
  columnPitch: number;
  rowCount: number;
}

/**
 * Lays the block out with its top at y = 0. Rows go into `rows` header first,
 * then planet rows, whichever way up they are stacked: `place` relies on it.
 * `headerLast` puts the house number and sign under the planets, which a
 * triangle pointing down needs when its wide top is the only place a crowd
 * of planets fits.
 */
function shapeBlock(region: FitRegion, size: number, columns: number, headerLast: boolean, measure: MeasureText, options: FitOptions): BlockShape {
  const headerLines = region.header ?? [];
  const headerHeight = headerLines.reduce((sum, line) => sum + line.size * HEADER_LINE, 0)
    + (headerLines.length && region.entries.length ? HEADER_GAP : 0);

  const widths = region.entries.map((entry) => entryWidth(entry, size, measure, options));
  const columnWidth = Math.max(0, ...widths);
  const gap = size * 0.5;
  const columnPitch = columnWidth + gap;
  const rowHeight = size * LINE;
  const rowCount = Math.ceil(region.entries.length / columns);

  const rows: Box[] = [];
  const header: { dy: number; size: number }[] = [];
  let y = headerLast ? rowCount * rowHeight + (headerLines.length && region.entries.length ? HEADER_GAP : 0) : 0;
  for (const line of headerLines) {
    const h = line.size * HEADER_LINE;
    const w = measure(line.text, line.size, line.kind);
    rows.push({ x: -w / 2, y, w, h });
    header.push({ dy: y + h / 2, size: line.size });
    y += h;
  }

  y = headerLast ? 0 : headerHeight;
  const entries: { dx: number; dy: number; row: number }[] = [];
  for (let r = 0; r < rowCount; r++) {
    const inRow = Math.min(columns, region.entries.length - r * columns);
    const rowWidth = columns === 1 ? widths[r] : inRow * columnWidth + (inRow - 1) * gap;
    rows.push({ x: -rowWidth / 2, y, w: rowWidth, h: rowHeight });
    for (let c = 0; c < inRow; c++) {
      entries.push({ dx: (c - (inRow - 1) / 2) * columnPitch, dy: y + rowHeight / 2, row: r });
    }
    y += rowHeight;
  }
  return { height: headerHeight + rowCount * rowHeight, rows, header, entries, rowHeight, columnPitch, rowCount };
}

/**
 * How much each choice costs, in steps of type size. A short single stack
 * with its house number on top reads most like a hand-drawn chart, so a
 * column, a header moved underneath or a row nudged sideways each has to buy
 * real size to be chosen.
 */
const COLUMN_COST = 1.5;
const HEADER_LAST_COST = 2;
const SHIFT_COST = 0.75;

function candidates(count: number, hasHeader: boolean, options: FitOptions): Candidate[] {
  const list: Candidate[] = [];
  for (let size = options.maxSize; size >= options.minSize - 1e-6; size -= 0.5) {
    for (let columns = 1; columns <= Math.min(3, Math.max(1, count)); columns++) {
      for (const headerLast of hasHeader ? [false, true] : [false]) {
        list.push({ size, columns, headerLast, score: size - (columns - 1) * COLUMN_COST - (headerLast ? HEADER_LAST_COST : 0) });
      }
    }
  }
  return list.sort((a, b) => b.score - a.score || a.columns - b.columns || b.size - a.size);
}

/** Offsets tried around the anchor, nearest first. */
function offsets(): Point[] {
  const list: Point[] = [];
  for (let dy = -96; dy <= 96; dy += 4) {
    for (const dx of [0, -12, 12, -24, 24]) list.push([dx, dy]);
  }
  return list.sort((a, b) => (Math.abs(a[0]) * 1.5 + Math.abs(a[1])) - (Math.abs(b[0]) * 1.5 + Math.abs(b[1])));
}

const OFFSETS = offsets();

/** How far a single row may move sideways to clear a slanted edge or a corner label. */
const ROW_REACH = 32;

export function fitRegion(region: FitRegion, measure: MeasureText, options: FitOptions): FitResult {
  const exclude = region.exclude ?? [];
  const edges = edgesOf(region.poly, options.margin);
  const minY = Math.min(...region.poly.map(([, y]) => y)) + options.margin;
  const maxY = Math.max(...region.poly.map(([, y]) => y)) - options.margin;
  // Below the minimum only when a house cannot hold its planets otherwise
  // (a stellium in a corner): smaller type beats text across the lines.
  const hasHeader = !!region.header?.length;
  const list = [
    ...candidates(region.entries.length, hasHeader, options),
    ...candidates(region.entries.length, hasHeader, { ...options, maxSize: options.minSize - 0.5, minSize: options.floorSize }),
  ];
  let best: { score: number; result: FitResult } | null = null;
  for (const candidate of list) {
    // Sorted by score, so nothing later can beat what is already found.
    if (best && candidate.score <= best.score) break;
    const block = shapeBlock(region, candidate.size, candidate.columns, candidate.headerLast, measure, options);
    if (block.height > maxY - minY) continue;
    for (const [dx, dy] of OFFSETS) {
      const cx = region.anchor[0] + dx;
      const top = region.anchor[1] + dy - block.height / 2;
      if (top < minY || top + block.height > maxY) continue;
      const shifts: number[] = [];
      const ok = block.rows.every((row) => {
        const centre = rowCentre(edges, exclude, options.margin / 2, top + row.y, top + row.y + row.h, row.w, cx, ROW_REACH);
        if (centre === null) return false;
        shifts.push(Math.abs(centre - cx) < 0.5 ? 0 : centre - cx);
        return true;
      });
      if (!ok) continue;
      const score = candidate.score - shifts.filter((s) => s !== 0).length * SHIFT_COST;
      if (!best || score > best.score) best = { score, result: place(block, candidate, cx, top, shifts, true) };
      break;
    }
  }
  if (best) return best.result;
  // Still nothing: let a large-text header give back its zoom, then try again.
  if (region.header?.length && !region.headerShrunk) {
    return fitRegion({
      ...region,
      headerShrunk: true,
      header: region.header.map((line) => ({ ...line, size: line.size * 0.75 })),
    }, measure, options);
  }
  // Nothing fits: smallest size, most columns, at the anchor.
  const columns = Math.min(3, Math.max(1, region.entries.length));
  const fallback = { size: options.floorSize, columns, headerLast: false, score: 0 };
  const block = shapeBlock(region, fallback.size, fallback.columns, false, measure, options);
  return place(block, fallback, region.anchor[0], region.anchor[1] - block.height / 2, block.rows.map(() => 0), false);
}

function place(block: BlockShape, candidate: Candidate, cx: number, top: number, shifts: number[], fitted: boolean): FitResult {
  const headerCount = block.header.length;
  return {
    size: candidate.size,
    columns: candidate.columns,
    header: block.header.map((line, i) => ({ x: cx + shifts[i], y: top + line.dy, size: line.size })),
    entries: block.entries.map((entry) => ({
      x: cx + entry.dx + shifts[headerCount + entry.row],
      y: top + entry.dy,
      size: candidate.size,
    })),
    rowHeight: block.rowHeight,
    columnPitch: block.columnPitch,
    rows: block.rowCount,
    fitted,
  };
}

/**
 * Box of a one-line label drawn with dominant-baseline: middle.
 * `anchor` is the SVG text-anchor.
 */
export function labelBox(x: number, y: number, width: number, size: number, anchor: 'start' | 'middle' | 'end'): Box {
  const left = anchor === 'start' ? x : anchor === 'end' ? x - width : x - width / 2;
  return { x: left, y: y - size * 0.6, w: width, h: size * 1.2 };
}

/** Rough widths for when there is no canvas to measure with (tests, server). */
export const estimateText: MeasureText = (text, size, kind) => {
  const perChar = kind === 'symbol' ? 0.95 : kind === 'label' ? 0.72 : 0.64;
  return [...text].length * perChar * size;
};
