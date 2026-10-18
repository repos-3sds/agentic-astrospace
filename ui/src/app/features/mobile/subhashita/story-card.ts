import { Subhashita, SUBHASHITA_TITLE } from '../../../core/subhashita.service';

/** WhatsApp and Instagram statuses are 9:16; 1080 wide is what both keep sharp. */
export const STORY_WIDTH = 1080;
export const STORY_HEIGHT = 1920;

const SIDE = 110;
const SANS = `'Inter', system-ui, sans-serif`;
const SERIF = `'Noto Serif Devanagari', 'Noto Sans Devanagari', serif`;
const ITALIC = `'Playfair Display', Georgia, serif`;
/** The wordmark face the app uses for its name (styles.scss .siddha-brand). */
const BRAND = `'Samarkan', 'Playfair Display', serif`;

/** Fixed, so every share of a day's verse is the same picture. */
const STARS: [number, number, number][] = [
  [0.14, 0.11, 3], [0.84, 0.08, 4], [0.94, 0.34, 3], [0.05, 0.42, 4],
  [0.94, 0.79, 4], [0.17, 0.87, 3], [0.62, 0.17, 2], [0.05, 0.7, 2],
];

/**
 * Draws the shareable 9:16 card for a verse (Figma M10 "Share Story Card",
 * node 107:101): rust into near-black, a few fixed stars, the verse in the
 * middle and where it comes from underneath.
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

  const ground = ctx.createLinearGradient(0, 0, STORY_WIDTH, STORY_HEIGHT);
  ground.addColorStop(0, '#d2432f');
  ground.addColorStop(0.42, '#6e2419');
  ground.addColorStop(0.7, '#24150f');
  ground.addColorStop(1, '#1a120e');
  ctx.fillStyle = ground;
  ctx.fillRect(0, 0, STORY_WIDTH, STORY_HEIGHT);

  ctx.fillStyle = 'rgba(255, 240, 225, 0.55)';
  for (const [x, y, r] of STARS) {
    ctx.beginPath();
    ctx.arc(x * STORY_WIDTH, y * STORY_HEIGHT, r * 2, 0, Math.PI * 2);
    ctx.fill();
  }

  const mid = STORY_WIDTH / 2;
  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = 'center';

  // The app's own wordmark (Samarkan, as on the welcome screen), not spaced
  // caps: a status is often the first time a friend sees the name.
  ctx.fillStyle = '#fff4e6';
  ctx.font = `400 92px ${BRAND}`;
  ctx.fillText('Siddha', mid, 210);

  // Each block is measured first, then the whole stack is centred, so a
  // long verse and a short one both sit in the middle of the card.
  const width = STORY_WIDTH - SIDE * 2;
  const sanskrit = fitLines(ctx, verse.sanskrit.split('\n'), width, SERIF, 46, 32, 6, 400, false);
  const english = fitLines(ctx, [verse.english], width - 40, SANS, 54, 40, 6, 600, true);
  const meaning = verse.meaning
    ? fitLines(ctx, [verse.meaning], width - 80, ITALIC, 38, 30, 3, 400, true)
    : null;
  const sourceLine = `— ${verse.source} ${verse.ref}`;

  const gap = 64;
  const head = 30 + 46;
  const rule = meaning ? 44 + 2 + 44 : 0;
  const height = head + gap + sanskrit.height + gap + english.height
    + (meaning ? rule + meaning.height : 0) + gap + 40;
  let y = Math.max(330, (STORY_HEIGHT - height) / 2 - 20);

  ctx.fillStyle = 'rgba(255, 236, 220, 0.72)';
  ctx.font = `500 28px ${SANS}`;
  y += 30;
  drawSpaced(ctx, SUBHASHITA_TITLE.toUpperCase(), mid, y, 5, 'center');
  ctx.font = `400 30px ${SANS}`;
  y += 46;
  ctx.fillText(longDate(verse.date), mid, y);
  y += gap;

  ctx.fillStyle = 'rgba(255, 236, 220, 0.9)';
  ctx.font = `400 ${sanskrit.size}px ${SERIF}`;
  for (const line of sanskrit.lines) {
    y += sanskrit.lineHeight;
    ctx.fillText(line, mid, y);
  }
  y += gap;

  ctx.fillStyle = '#fff8ec';
  ctx.font = `600 ${english.size}px ${SANS}`;
  for (const line of english.lines) {
    y += english.lineHeight;
    ctx.fillText(line, mid, y);
  }

  if (meaning) {
    y += 44;
    ctx.fillStyle = 'rgba(240, 195, 107, 0.7)';
    ctx.fillRect(mid - 40, y, 80, 2);
    y += 2 + 44;
    ctx.fillStyle = 'rgba(255, 236, 220, 0.8)';
    ctx.font = `italic 400 ${meaning.size}px ${ITALIC}`;
    for (const line of meaning.lines) {
      y += meaning.lineHeight;
      ctx.fillText(line, mid, y);
    }
  }
  y += gap;

  ctx.fillStyle = 'rgba(255, 236, 220, 0.72)';
  ctx.font = `500 34px ${SANS}`;
  ctx.fillText(sourceLine, mid, y + 34);

  ctx.fillStyle = 'rgba(255, 236, 220, 0.6)';
  ctx.font = `400 30px ${SANS}`;
  ctx.fillText('A verse a day in the Siddha app · asksiddha.app', mid, STORY_HEIGHT - 120);
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
  const meaning = verse.meaning ? `\n${verse.meaning}\n` : '';
  return `${verse.sanskrit}\n\n“${verse.english}”\n— ${verse.source} ${verse.ref}\n${meaning}\n${SUBHASHITA_TITLE}, from the Siddha app: https://asksiddha.app`;
}

/** "Friday, 17 October", built from the parts so no timezone can move the day. */
export function longDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return `${date.toLocaleDateString('en-GB', { weekday: 'long' })}, ${d} ${date.toLocaleDateString('en-GB', { month: 'long' })}`;
}

interface Fitted { lines: string[]; size: number; lineHeight: number; height: number }

/**
 * Wraps to the width, shrinking the type until it fits in `maxLines`. With
 * `balance`, the same number of lines is then spread evenly (the narrowest
 * width that still needs no more lines), so a verse doesn't end on a stub.
 */
function fitLines(ctx: CanvasRenderingContext2D, paragraphs: string[], width: number, family: string,
                  largest: number, smallest: number, maxLines: number, weight: number | string,
                  balance: boolean): Fitted {
  let size = largest;
  for (;;) {
    ctx.font = `${weight} ${size}px ${family}`;
    let lines = paragraphs.flatMap((p) => wrap(ctx, p, width));
    if (lines.length <= maxLines || size <= smallest) {
      if (balance && lines.length > 1) lines = balanced(ctx, paragraphs, width, lines.length);
      const lineHeight = Math.round(size * 1.34);
      return { lines, size, lineHeight, height: lines.length * lineHeight };
    }
    size -= 2;
  }
}

function balanced(ctx: CanvasRenderingContext2D, paragraphs: string[], width: number, count: number): string[] {
  let low = width * 0.5;
  let high = width;
  while (high - low > 4) {
    const trial = (low + high) / 2;
    if (paragraphs.flatMap((p) => wrap(ctx, p, trial)).length <= count) high = trial;
    else low = trial;
  }
  return paragraphs.flatMap((p) => wrap(ctx, p, high));
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
      fonts.load(`600 54px ${SANS}`),
      fonts.load(`400 92px ${BRAND}`, 'Siddha'),
      fonts.load(`italic 400 38px ${ITALIC}`),
      fonts.load(`500 30px ${SANS}`),
      fonts.load(`400 44px ${SERIF}`, 'धर्म'),
    ]);
  } catch { /* the system font draws instead */ }
}
