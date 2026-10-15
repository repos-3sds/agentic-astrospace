export type MobileSymbolKind = 'tithi' | 'nakshatra' | 'color' | 'gem' | 'direction';

export interface MobileSymbol {
  kind: MobileSymbolKind;
  glyph: string;
  label: string;
  color?: string;
  angle?: number;
}

const TITHI_ORDER = [
  'pratipada',
  'dvitiya',
  'tritiya',
  'chaturthi',
  'panchami',
  'shashthi',
  'saptami',
  'ashtami',
  'navami',
  'dashami',
  'ekadashi',
  'dwadashi',
  'trayodashi',
  'chaturdashi',
  'purnima',
  'pratipada',
  'dvitiya',
  'tritiya',
  'chaturthi',
  'panchami',
  'shashthi',
  'saptami',
  'ashtami',
  'navami',
  'dashami',
  'ekadashi',
  'dwadashi',
  'trayodashi',
  'chaturdashi',
  'amavasya',
];

const NAKSHATRA_SYMBOLS: Record<string, string> = {
  ashwini: '♞',
  asvini: '♞',
  bharani: '▽',
  krittika: '✦',
  kritika: '✦',
  rohini: '✧',
  mrigashira: '◇',
  mrigasirsha: '◇',
  ardra: '◌',
  punarvasu: '⌂',
  pushya: '✿',
  ashlesha: '∿',
  aslesha: '∿',
  magha: '♛',
  'purva phalguni': '▱',
  'uttara phalguni': '▰',
  hasta: '✋',
  chitra: '◆',
  swati: '✤',
  vishakha: '⌁',
  anuradha: '☂',
  jyeshtha: '◎',
  jyestha: '◎',
  mula: '⌄',
  moola: '⌄',
  'purva ashadha': '◒',
  'uttara ashadha': '◓',
  shravana: '☊',
  sravana: '☊',
  dhanishta: '◈',
  shatabhisha: '○',
  satabhisha: '○',
  'purva bhadrapada': '▵',
  'uttara bhadrapada': '▴',
  revati: '⌒',
};

const GEM_COLORS: Record<string, string> = {
  ruby: '#c9273a',
  pearl: '#f4eee3',
  coral: '#e76f51',
  emerald: '#1f9d66',
  'yellow sapphire': '#e2b93f',
  diamond: '#dbeafe',
  'blue sapphire': '#2d5bd1',
  hessonite: '#b86f19',
  catseye: '#8b9467',
  "cat's eye": '#8b9467',
  garnet: '#8f1d2c',
  amethyst: '#8f5bd7',
  turquoise: '#23a6a6',
};

const DIRECTION_ANGLES: Record<string, number> = {
  north: 0,
  northeast: 45,
  'north east': 45,
  east: 90,
  southeast: 135,
  'south east': 135,
  south: 180,
  southwest: 225,
  'south west': 225,
  west: 270,
  northwest: 315,
  'north west': 315,
};

export function tithiSymbol(value: string): MobileSymbol {
  const key = normalize(value);
  const explicitIndex = TITHI_ORDER.findIndex((name, index) => key.includes(name) && (
    name !== 'pratipada' || key.includes(index < 15 ? 'shukla' : 'krishna') || !key.includes('krishna')
  ));
  let index = explicitIndex >= 0 ? explicitIndex + 1 : 0;
  if (key.includes('amavasya')) index = 30;
  if (key.includes('purnima') || key.includes('paurnami')) index = 15;
  return { kind: 'tithi', glyph: moonGlyphForTithi(index), label: value };
}

export function nakshatraSymbol(value: string): MobileSymbol {
  const key = normalize(value);
  const match = Object.keys(NAKSHATRA_SYMBOLS)
    .sort((a, b) => b.length - a.length)
    .find((name) => key.includes(name));
  return { kind: 'nakshatra', glyph: match ? NAKSHATRA_SYMBOLS[match] : '✦', label: value };
}

export function colorSymbol(name: string, hex?: string): MobileSymbol {
  return { kind: 'color', glyph: '', label: name, color: safeColor(hex) ?? colorFromName(name) };
}

export function gemSymbol(value: string): MobileSymbol {
  const key = normalize(value);
  const match = Object.keys(GEM_COLORS).find((name) => key.includes(name));
  return { kind: 'gem', glyph: '◆', label: value, color: match ? GEM_COLORS[match] : '#9f8f7b' };
}

export function directionSymbol(value: string): MobileSymbol {
  const key = normalize(value);
  const match = Object.keys(DIRECTION_ANGLES).find((name) => key.includes(name));
  return { kind: 'direction', glyph: '↑', label: value, angle: match ? DIRECTION_ANGLES[match] : 0 };
}

function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function moonGlyphForTithi(index: number): string {
  if (index === 30) return '🌑';
  if (index === 15) return '🌕';
  if (index >= 1 && index <= 4) return '🌒';
  if (index >= 5 && index <= 9) return '🌓';
  if (index >= 10 && index <= 14) return '🌔';
  if (index >= 16 && index <= 19) return '🌖';
  if (index >= 20 && index <= 24) return '🌗';
  if (index >= 25 && index <= 29) return '🌘';
  return '◐';
}

function safeColor(hex?: string): string | null {
  return hex && /^#[0-9a-f]{6}$/i.test(hex) ? hex : null;
}

function colorFromName(name: string): string {
  const key = normalize(name);
  if (key.includes('emerald')) return '#15915f';
  if (key.includes('red') || key.includes('ruby')) return '#c9473d';
  if (key.includes('yellow') || key.includes('gold')) return '#d7a52c';
  if (key.includes('blue')) return '#3266d5';
  if (key.includes('green')) return '#2f9c68';
  if (key.includes('white') || key.includes('pearl')) return '#f3eee6';
  if (key.includes('black')) return '#202431';
  if (key.includes('orange') || key.includes('coral')) return '#df7044';
  if (key.includes('violet') || key.includes('purple')) return '#8b5bd1';
  return '#b13f2e';
}
