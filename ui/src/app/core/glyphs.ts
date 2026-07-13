/**
 * Astronomical glyphs and per-sign colors.
 * Unicode astrological symbols rendered in the display font — never emoji.
 */

export interface SignMeta {
  glyph: string;
  color: string;
}

export const ZODIAC: Record<string, SignMeta> = {
  Aries: { glyph: '♈', color: '#f0605a' },
  Taurus: { glyph: '♉', color: '#4cc38a' },
  Gemini: { glyph: '♊', color: '#e8c468' },
  Cancer: { glyph: '♋', color: '#5ea9f2' },
  Leo: { glyph: '♌', color: '#f2994a' },
  Virgo: { glyph: '♍', color: '#7bc86c' },
  Libra: { glyph: '♎', color: '#b18af8' },
  Scorpio: { glyph: '♏', color: '#e05666' },
  Sagittarius: { glyph: '♐', color: '#9b7df0' },
  Capricorn: { glyph: '♑', color: '#8d91b0' },
  Aquarius: { glyph: '♒', color: '#56b8e0' },
  Pisces: { glyph: '♓', color: '#4fd1c5' },
};

export const SIGN_ORDER = Object.keys(ZODIAC);

export const PLANET_GLYPHS: Record<string, string> = {
  Sun: '☉',
  Moon: '☽',
  Mercury: '☿',
  Venus: '♀',
  Mars: '♂',
  Jupiter: '♃',
  Saturn: '♄',
  Uranus: '♅',
  Neptune: '♆',
  Pluto: '♇',
  Rahu: '☊',
  Ketu: '☋',
  'North Node': '☊',
  'True Node': '☊',
  Chiron: '⚷',
};

export function signMeta(sign?: string | null): SignMeta {
  return (sign && ZODIAC[sign]) || { glyph: '✦', color: 'var(--as-accent)' };
}

export function planetGlyph(name: string): string {
  return PLANET_GLYPHS[name] ?? '✦';
}

export const DIGNITY_COLORS: Record<string, string> = {
  Exalted: 'var(--as-good)',
  Moolatrikona: 'var(--as-good)',
  Own: 'var(--as-good)',
  Friendly: 'var(--as-text)',
  Neutral: 'var(--as-muted)',
  Enemy: 'var(--as-warn)',
  'Great Enemy': 'var(--as-bad)',
  Debilitated: 'var(--as-bad)',
};
