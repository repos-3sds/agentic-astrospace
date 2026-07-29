import { Kundli, VargaChart, VedicAll, VedicPlanet } from '../../../core/models';
import { ChartCell } from './east-chart.component';
import { PlanetDetail } from './planet-sheet.component';

export const SIGN_ORDER = [
  'Aries',
  'Taurus',
  'Gemini',
  'Cancer',
  'Leo',
  'Virgo',
  'Libra',
  'Scorpio',
  'Sagittarius',
  'Capricorn',
  'Aquarius',
  'Pisces',
];

export const SIGN_SHORT: Record<string, string> = {
  Aries: 'Ar',
  Taurus: 'Ta',
  Gemini: 'Ge',
  Cancer: 'Cn',
  Leo: 'Le',
  Virgo: 'Vi',
  Libra: 'Li',
  Scorpio: 'Sc',
  Sagittarius: 'Sg',
  Capricorn: 'Cp',
  Aquarius: 'Aq',
  Pisces: 'Pi',
};

export const PLANET_ABBR: Record<string, string> = {
  Ascendant: 'As',
  Sun: 'Su',
  Moon: 'Mo',
  Mars: 'Ma',
  Mercury: 'Me',
  Jupiter: 'Ju',
  Venus: 'Ve',
  Saturn: 'Sa',
  Rahu: 'Ra',
  Ketu: 'Ke',
};

export const PLANET_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(PLANET_ABBR).map(([name, abbr]) => [abbr, name]),
);

const EAST_ANCHORS: Record<string, { x: number; y: number }> = {
  Taurus: { x: 50, y: 12 },
  Gemini: { x: 70, y: 12 },
  Cancer: { x: 86, y: 24 },
  Leo: { x: 82, y: 48 },
  Virgo: { x: 84, y: 72 },
  Libra: { x: 70, y: 86 },
  Scorpio: { x: 50, y: 80 },
  Sagittarius: { x: 30, y: 86 },
  Capricorn: { x: 14, y: 72 },
  Aquarius: { x: 18, y: 48 },
  Pisces: { x: 30, y: 12 },
  Aries: { x: 14, y: 24 },
};

const PLANET_ORDER = ['Ascendant', 'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu'];

export interface ChartAdapterResult {
  cells: ChartCell[];
  details: Record<string, PlanetDetail>;
  angles: { label: string; sign: string; degree: string }[];
  signature: { headline: string; detail: string };
  provenance: { label: string; value: string }[];
}

export function buildChartAdapter(data: VedicAll, profile: Kundli | null, vargaId = 'D1'): ChartAdapterResult {
  const varga = data.vargas?.[vargaId] ?? null;
  const lagnaSign = varga?.lagna?.sign ?? profile?.ascendant ?? data.avkahada?.['rashi'] ?? '—';
  const grouped = groupPlanets(data, varga);
  grouped[lagnaSign] = ['Ascendant', ...(grouped[lagnaSign] ?? [])];

  const cells = SIGN_ORDER.map((sign) => {
    const anchor = EAST_ANCHORS[sign];
    const planets = [...new Set(grouped[sign] ?? [])]
      .sort((a, b) => PLANET_ORDER.indexOf(a) - PLANET_ORDER.indexOf(b))
      .map((planet) => PLANET_ABBR[planet] ?? planet.slice(0, 2))
      .join(' · ');
    return { sign: SIGN_SHORT[sign] ?? sign.slice(0, 2), planets: planets || undefined, x: anchor.x, y: anchor.y };
  });

  const details: Record<string, PlanetDetail> = {
    As: {
      abbr: 'As',
      title: `Ascendant in ${lagnaSign}`,
      position: `${SIGN_SHORT[lagnaSign] ?? lagnaSign} · chart anchor`,
      house: '1st house',
      reading: `The chart is anchored by ${lagnaSign}. This is the reference point for houses and chart style, computed from the saved birth details.`,
    },
  };
  for (const [planet, row] of Object.entries(data.planets ?? {})) {
    const abbr = PLANET_ABBR[planet] ?? planet.slice(0, 2);
    details[abbr] = planetDetail(planet, abbr, row);
  }

  const sun = data.planets?.['Sun'];
  const moon = data.planets?.['Moon'];
  const angles = [
    { label: 'SUN', sign: sun?.sign ?? profile?.sun_sign ?? '—', degree: degreeLabel(sun) },
    { label: 'MOON', sign: moon?.sign ?? profile?.moon_sign ?? '—', degree: degreeLabel(moon) },
    { label: 'ASCENDANT', sign: lagnaSign, degree: data.meta?.sidereal_time ? 'from birth time' : 'computed' },
  ];
  const signature = {
    headline: `${angles[0].sign} Sun, ${angles[1].sign} Moon, ${lagnaSign} rising.`,
    detail: `${profile?.name ?? 'This profile'} is shown from the real chart payload using ${data.meta?.ayanamsha?.name ?? 'the selected'} ayanamsha.`,
  };

  return { cells, details, angles, signature, provenance: provenanceRows(data, profile) };
}

function groupPlanets(data: VedicAll, varga: VargaChart | null): Record<string, string[]> {
  const grouped: Record<string, string[]> = {};
  const source = varga?.planets
    ? Object.fromEntries(Object.entries(varga.planets).map(([planet, row]) => [planet, row.sign]))
    : Object.fromEntries(Object.entries(data.planets ?? {}).map(([planet, row]) => [planet, row.sign]));
  for (const [planet, sign] of Object.entries(source)) {
    if (!sign) continue;
    grouped[sign] = [...(grouped[sign] ?? []), planet];
  }
  return grouped;
}

function planetDetail(planet: string, abbr: string, row: VedicPlanet): PlanetDetail {
  const house = row.house ? `${ordinal(row.house)} house` : 'house unavailable';
  return {
    abbr,
    title: `${planet} in ${row.sign}`,
    position: `${row.dms ?? degreeLabel(row)} · ${house}`,
    house,
    reading: [
      `${planet} is in ${row.sign}${row.nakshatra ? `, ${row.nakshatra} pada ${row.nakshatra_pada}` : ''}.`,
      row.retrograde ? 'It is marked retrograde in the returned calculation.' : null,
      `This detail is computed from the selected profile rather than fixed example text.`,
    ].filter(Boolean).join(' '),
  };
}

function provenanceRows(data: VedicAll, profile: Kundli | null): { label: string; value: string }[] {
  const provenance = data.provenance;
  return [
    { label: 'Ephemeris', value: provenance?.engine ?? 'Backend calculation engine' },
    { label: 'Ayanamsha', value: data.meta?.ayanamsha?.name ?? provenance?.ayanamsha ?? '—' },
    { label: 'Node type', value: provenance?.node_type ?? data.meta?.node_type ?? '—' },
    { label: 'House system', value: provenance?.house_system ?? 'Whole-sign' },
    { label: 'Calculation place', value: provenance?.calculation_place?.city ?? data.meta?.place ?? profile?.birth_city ?? '—' },
    { label: 'Birth time confidence', value: profile?.notes?.toLowerCase().includes('approx') ? 'Approximate' : 'Provided' },
  ];
}

function degreeLabel(row?: Pick<VedicPlanet, 'dms' | 'degree_in_sign'> | null): string {
  if (!row) return '—';
  if (row.dms) return row.dms;
  if (typeof row.degree_in_sign === 'number') return `${row.degree_in_sign.toFixed(2)} deg`;
  return '—';
}

function ordinal(value: number): string {
  const suffix = value % 10 === 1 && value !== 11 ? 'st' : value % 10 === 2 && value !== 12 ? 'nd' : value % 10 === 3 && value !== 13 ? 'rd' : 'th';
  return `${value}${suffix}`;
}
