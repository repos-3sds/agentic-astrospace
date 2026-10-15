/** One "Show me why" link from a reading into the chart screen behind it. */
export interface DrillDown {
  label: string;
  detail: string;
  route: string[];
  queryParams?: Record<string, string>;
}

const TARGETS: { match: RegExp; link: DrillDown }[] = [
  {
    match: /\b(maha|antar|pratyantar)?dasha|bhukti|\bperiod\b/i,
    link: { label: 'Your life period', detail: 'The dasha running now', route: ['/m', 'chart', 'periods'] },
  },
  {
    match: /transit|gochar|sade ?sati|\bmoving\b/i,
    link: { label: 'Today’s transits', detail: 'Where the planets are now', route: ['/m', 'transits'] },
  },
  {
    match: /\byoga\b|yogas|dosha|manglik|kuja|kaal ?sarp/i,
    link: { label: 'Yogas & doshas', detail: 'With their cancellations', route: ['/m', 'chart', 'yogas'] },
  },
  {
    match: /navamsa|\bd-?9\b|\bd-?10\b|varga|divisional/i,
    link: { label: 'Divisional charts', detail: 'Navamsa and the vargas', route: ['/m', 'chart', 'full'], queryParams: { varga: 'D9' } },
  },
  {
    match: /shadbala|strength|ashtakavarga|bindu/i,
    link: { label: 'Planet strength', detail: 'Shadbala and ashtakavarga', route: ['/m', 'chart', 'strength'] },
  },
  {
    match: /lagna|ascendant|nakshatra|rashi|\bhouse\b|lord/i,
    link: { label: 'Your birth chart', detail: 'Lagna, houses and placements', route: ['/m', 'chart'] },
  },
];

const BIRTH_CHART = TARGETS[TARGETS.length - 1].link;

/**
 * The chart screens a reading's own evidence points at, at most three, in
 * the order the evidence mentions them. Under the Ask-first tab bar these
 * screens are reached this way rather than from tabs (checklist D1), so the
 * link has to go to the screen that actually holds the factor named, not a
 * generic chart page. `lead` names screens a caller knows its reading is
 * built from, ahead of whatever the evidence mentions.
 */
export function whyDrillDowns(evidence: readonly string[], lead: readonly DrillDown[] = []): DrillDown[] {
  const text = evidence.join(' \n ');
  const found = TARGETS
    .map((target) => ({ link: target.link, at: text.search(target.match) }))
    .filter((hit) => hit.at >= 0)
    .sort((a, b) => a.at - b.at)
    .map((hit) => hit.link);
  const links = [...new Set([...lead, ...found])];
  if (!links.includes(BIRTH_CHART)) links.push(BIRTH_CHART);
  return links.slice(0, 3);
}

/** What every day-reading is built from: the running dasha and the transits over the chart. */
export const TODAY_DRILL_DOWNS: readonly DrillDown[] = [TARGETS[0].link, TARGETS[1].link];
