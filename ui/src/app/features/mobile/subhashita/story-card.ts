import { Subhashita, SUBHASHITA_TITLE } from '../../../core/subhashita.service';

/** WhatsApp and Instagram statuses are 9:16; 1080 wide is what both keep sharp. */
export const STORY_WIDTH = 1080;
export const STORY_HEIGHT = 1920;

const SIDE = 120;
const MID = STORY_WIDTH / 2;
const SANS = `'Inter', system-ui, sans-serif`;
const DISPLAY = `'Playfair Display', Georgia, serif`;
const SERIF = `'Noto Serif Devanagari', 'Noto Sans Devanagari', serif`;
/** The brand wordmark face, the same one as the welcome screen's "Siddha". */
const BRAND = `'Samarkan', 'Cormorant Garamond', serif`;

const CREAM = '#fff8ec';
const SOFT = 'rgba(255, 236, 220, 0.74)';
const GOLD = '#f2c98a';

/** Fixed, so every share of a day's verse is the same picture; kept to the edges. */
const STARS: [number, number, number][] = [
  [0.08, 0.06, 3], [0.9, 0.05, 4], [0.95, 0.3, 3], [0.04, 0.38, 3],
  [0.95, 0.66, 4], [0.05, 0.8, 3], [0.93, 0.9, 2], [0.06, 0.55, 2],
];

/**
 * Draws the shareable 9:16 card for a verse (Figma M10 "Share Story Card",
 * node 107:101): rust into near-black and a few fixed stars.
 *
 * One centred column with a set rhythm (Hawk, 2026-10-18: the first card was
 * neither aligned nor pleasant to look at). The wordmark in the brand face
 * heads it and the footer closes it; between them the verse block is
 * centred as a whole: title and date, the Sanskrit, a rule, the English in
 * the display serif, the plain meaning in gold, and the source in small caps.
 *
 * Fixed colours on purpose: a status is seen on other people's phones in
 * whatever theme they use, so the card cannot follow this reader's theme.
 */
export async function renderStoryCard(verse: Subhashita, canvas = document.createElement('canvas')): Promise<HTMLCanvasElement> {
  await fontsReady();
  canvas.width = STORY_WIDTH;
  canvas.height = STORY_HEIGHT;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('This device could not draw the image.');

  const ground = ctx.createLinearGradient(0, 0, STORY_WIDTH * 0.6, STORY_HEIGHT);
  ground.addColorStop(0, '#c9402c');
  ground.addColorStop(0.4, '#6e2419');
  ground.addColorStop(0.72, '#24150f');
  ground.addColorStop(1, '#1a120e');
  ctx.fillStyle = ground;
  ctx.fillRect(0, 0, STORY_WIDTH, STORY_HEIGHT);

  ctx.fillStyle = 'rgba(255, 240, 225, 0.5)';
  for (const [x, y, r] of STARS) {
    ctx.beginPath();
    ctx.arc(x * STORY_WIDTH, y * STORY_HEIGHT, r * 2, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = 'center';

  // Head: the wordmark, then a small ornament under it.
  ctx.fillStyle = CREAM;
  ctx.font = `400 92px ${BRAND}`;
  ctx.fillText('Siddha', MID, 250);
  ornament(ctx, 300);

  // Foot: where the verse comes from, always at the same place.
  ctx.fillStyle = 'rgba(255, 236, 220, 0.6)';
  ctx.font = `400 30px ${SANS}`;
  ctx.fillText('A verse a day in the Siddha app  ·  asksiddha.app', MID, STORY_HEIGHT - 110);

  // Body, measured first so the whole block sits centred between head and foot.
  const width = STORY_WIDTH - SIDE * 2;
  const sanskrit = fitLines(ctx, verse.sanskrit.split('\n'), width, SERIF, 40, 30, 6, 400);
  const english = fitLines(ctx, [`“${verse.english}”`], width, DISPLAY, 48, 38, 7, 500, 'italic');
  const meaning = verse.meaning
    ? fitLines(ctx, [verse.meaning], width - 40, SANS, 38, 30, 3, 600)
    : null;

  const titleBlock = 28 + 18 + 30;
  const gap = 64;
  const ruleBlock = 2;
  const sourceBlock = 28;
  const meaningBlock = meaning ? 26 + 22 + meaning.height + gap : 0;
  const height = titleBlock + gap + sanskrit.height + gap + ruleBlock + gap
    + english.height + gap + meaningBlock + sourceBlock;
  const top = 380;
  const bottom = STORY_HEIGHT - 200;
  let y = Math.max(top, top + (bottom - top - height) / 2);

  ctx.fillStyle = SOFT;
  ctx.font = `600 28px ${SANS}`;
  y += 28;
  drawSpaced(ctx, SUBHASHITA_TITLE.toUpperCase(), MID, y, 6, 'center');
  ctx.font = `400 30px ${SANS}`;
  y += 18 + 30;
  ctx.fillText(longDate(verse.date), MID, y);
  y += gap;

  ctx.fillStyle = 'rgba(255, 236, 220, 0.86)';
  ctx.font = `400 ${sanskrit.size}px ${SERIF}`;
  y = drawLines(ctx, sanskrit, y);
  y += gap;

  ctx.fillStyle = 'rgba(242, 201, 138, 0.7)';
  ctx.fillRect(MID - 40, y, 80, ruleBlock);
  y += ruleBlock + gap;

  ctx.fillStyle = CREAM;
  ctx.font = `italic 500 ${english.size}px ${DISPLAY}`;
  y = drawLines(ctx, english, y);
  y += gap;

  if (meaning) {
    ctx.fillStyle = 'rgba(242, 201, 138, 0.8)';
    ctx.font = `600 24px ${SANS}`;
    y += 26;
    drawSpaced(ctx, 'WHAT IT MEANS', MID, y, 5, 'center');
    y += 22;
    ctx.fillStyle = GOLD;
    ctx.font = `600 ${meaning.size}px ${SANS}`;
    y = drawLines(ctx, meaning, y);
    y += gap;
  }

  ctx.fillStyle = SOFT;
  ctx.font = `600 26px ${SANS}`;
  y += sourceBlock;
  drawSpaced(ctx, `${verse.source} ${verse.ref}`.toUpperCase(), MID, y, 4, 'center');
  return canvas;
}

/** The card as a PNG file, ready for the share sheet. */
export async function storyCardFile(verse: Subhashita): Promise<File> {
  const canvas = await renderStoryCard(verse);
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'));
  if (!blob) throw new Error('This device could not save the image.');
  return new File([blob], `subhashita-${verse.date}.png`, { type: 'image/png' });
}

/** The words alone, for a share that is text rather than a picture. */
export function shareText(verse: Subhashita): string {
  const meaning = verse.meaning ? `\n\n${verse.meaning}` : '';
  return `${verse.sanskrit}\n\n“${verse.english}”\n— ${verse.source} ${verse.ref}${meaning}\n\n${SUBHASHITA_TITLE}, from the Siddha app: https://asksiddha.app`;
}

/** "Friday, 17 October", built from the parts so no timezone can move the day. */
export function longDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return `${date.toLocaleDateString('en-GB', { weekday: 'long' })}, ${d} ${date.toLocaleDateString('en-GB', { month: 'long' })}`;
}

interface Fitted { lines: string[]; size: number; lineHeight: number; height: number }

/** Wraps to the width, shrinking the type until it fits in `maxLines`. */
function fitLines(ctx: CanvasRenderingContext2D, paragraphs: string[], width: number, family: string,
                  largest: number, smallest: number, maxLines: number, weight: number, style = ''): Fitted {
  let size = largest;
  for (;;) {
    ctx.font = `${style} ${weight} ${size}px ${family}`.trim();
    const lines = paragraphs.flatMap((p) => wrap(ctx, p, width));
    if (lines.length <= maxLines || size <= smallest) {
      const lineHeight = Math.round(size * 1.34);
      return { lines, size, lineHeight, height: lines.length * lineHeight };
    }
    size -= 2;
  }
}

/** Draws fitted lines from `y` (the top of the block); returns the bottom. */
function drawLines(ctx: CanvasRenderingContext2D, fitted: Fitted, y: number): number {
  for (const line of fitted.lines) {
    y += fitted.lineHeight;
    ctx.fillText(line, MID, y - Math.round(fitted.lineHeight - fitted.size) / 2);
  }
  return y;
}

/** A short rule with a dot in the middle, under the wordmark. */
function ornament(ctx: CanvasRenderingContext2D, y: number): void {
  ctx.fillStyle = 'rgba(242, 201, 138, 0.75)';
  ctx.fillRect(MID - 70, y, 52, 2);
  ctx.fillRect(MID + 18, y, 52, 2);
  ctx.beginPath();
  ctx.arc(MID, y + 1, 5, 0, Math.PI * 2);
  ctx.fill();
}

function wrap(ctx: CanvasRenderingContext2D, text: string, width: number): string[] {
  const lines: string[] = [];
  let line = '';
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word;
    if (line && ctx.measureText(next).width > width) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** Canvas has no letter-spacing everywhere yet, so caps are spaced by hand. */
function drawSpaced(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, spacing: number,
                    align: 'left' | 'center' = 'left'): void {
  const previous = ctx.textAlign;
  ctx.textAlign = 'left';
  const chars = [...text];
  const total = chars.reduce((sum, c) => sum + ctx.measureText(c).width, 0) + spacing * (chars.length - 1);
  let cursor = align === 'center' ? x - total / 2 : x;
  for (const c of chars) {
    ctx.fillText(c, cursor, y);
    cursor += ctx.measureText(c).width + spacing;
  }
  ctx.textAlign = previous;
}

async function fontsReady(): Promise<void> {
  const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
  if (!fonts) return;
  try {
    await Promise.all([
      fonts.load(`600 38px ${SANS}`),
      fonts.load(`400 30px ${SANS}`),
      fonts.load(`italic 500 48px ${DISPLAY}`),
      fonts.load(`400 92px ${BRAND}`, 'Siddha'),
      fonts.load(`400 44px ${SERIF}`, 'धर्म'),
    ]);
  } catch { /* the system font draws instead */ }
}
