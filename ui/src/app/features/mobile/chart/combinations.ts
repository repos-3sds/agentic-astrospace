import { DoshasPayload, ExplainedRule, ManglikException, YogaResult, YogasDoshasPayload } from '../../../core/models';

/**
 * One yoga or dosha card, answering the five questions every card must
 * (Hawk, 2026-10-29): what it is, why this chart has it, what it can mean,
 * what to do, what to avoid. Book sources never reach the screen; the chart
 * placements in `why` are the citation.
 */
export interface Combination {
  id: string;
  /** A flag is a dosha or a caution yoga: never hidden, on any plan. */
  flag: boolean;
  kind: 'yoga' | 'dosha';
  title: string;
  tag: string;
  tone: 'good' | 'gold' | 'neutral';
  what: string;
  why: string[];
  impact: string;
  do: string[];
  avoid: string[];
  howCommon: string;
  /** Classical cancellations or exceptions this chart meets. */
  softens: string[];
  /** What dims a yoga that is present. */
  weakened: string[];
  /** Exceptions checked that do not apply (Manglik). */
  alsoChecked: string[];
  /** Practitioner only: the classical condition and the engine's own triggers. */
  classical: string;
  triggers: string[];
  /** Flags only: traditions draw the line differently. */
  convention?: string;
}

export interface CheckedRow {
  id: string;
  title: string;
  note: string;
  item: Combination | null;
}

export interface CombinationView {
  strengths: Combination[];
  flags: Combination[];
  checked: CheckedRow[];
  hiddenYogas: number;
}

export type ExperienceMode = 'guided' | 'balanced' | 'practitioner';

/** Yogas every plan sees in full. Mirrors FREE_YOGAS in astrospace/api/vedic_routes.py. */
export const FREE_YOGAS = 2;

const STRENGTH_RANK: Record<string, number> = { strong: 3, severe: 3, moderate: 2, weak: 1, mild: 1 };
const YOGA_WORD: Record<string, string> = { strong: 'Strong', moderate: 'Medium', weak: 'Light' };
const FLAG_WORD: Record<string, string> = { strong: 'strong', severe: 'strong', moderate: 'medium', mild: 'light' };
const CONVENTION = 'Traditions draw this line a little differently, so another astrologer may read it differently.';
/** Rules shown as one card, with every planet pair listed under Why. */
const GROUPED = new Set(['raja_yoga', 'dhana_yoga']);

export function isFlag(row: { category?: string }): boolean {
  return (row.category ?? '').toLowerCase().includes('caution');
}

function baseName(row: YogaResult): string {
  if (row.rule_id && GROUPED.has(row.rule_id)) return row.name.split(':')[0].trim();
  return row.name;
}

function item(row: YogaResult & ExplainedRule, flag: boolean): Combination {
  const reader = row.reader ?? {};
  const strength = row.strength || 'moderate';
  return {
    id: row.rule_id && GROUPED.has(row.rule_id) ? row.rule_id : `${row.rule_id ?? row.name}:${row.name}`,
    flag,
    kind: 'yoga',
    title: baseName(row),
    tag: flag ? `Flag · ${FLAG_WORD[strength] ?? strength}` : YOGA_WORD[strength] ?? strength,
    tone: flag ? 'gold' : 'good',
    what: reader.what ?? row.lay_explanation ?? '',
    why: row.why ?? [],
    impact: reader.impact ?? '',
    do: reader.do ?? [],
    avoid: reader.avoid ?? [],
    howCommon: reader.how_common ?? '',
    softens: row.cancellations ?? [],
    weakened: row.weakened ?? [],
    alsoChecked: [],
    classical: row.rule,
    triggers: row.triggers ?? [],
    convention: flag ? CONVENTION : undefined,
  };
}

/** Raja and Dhana Yoga: one card each, strongest pair's grade, every pair's evidence. */
function merge(group: Combination[], rows: YogaResult[]): Combination {
  const best = rows.reduce((a, b) => ((STRENGTH_RANK[b.strength] ?? 0) > (STRENGTH_RANK[a.strength] ?? 0) ? b : a));
  const first = group[0];
  return {
    ...first,
    tag: YOGA_WORD[best.strength] ?? best.strength,
    why: group.flatMap((row) => row.why),
    weakened: [...new Set(group.flatMap((row) => row.weakened))],
    triggers: group.flatMap((row) => row.triggers),
  };
}

function doshaItems(doshas: DoshasPayload | null): { flags: Combination[]; checked: CheckedRow[] } {
  const flags: Combination[] = [];
  const checked: CheckedRow[] = [];
  if (!doshas) return { flags, checked };
  for (const [key, row] of Object.entries(doshas)) {
    if (!row) continue;
    const reader = row.reader ?? {};
    const title = key === 'manglik' ? 'Manglik (Kuja) Dosha' : row.name;
    if (!row.active) {
      checked.push({ id: key, title, note: 'not in your chart', item: null });
      continue;
    }
    const exceptions: ManglikException[] = 'exceptions' in row ? row.exceptions ?? [] : [];
    const met = exceptions.filter((e) => e.applies);
    const severity = ('net_severity' in row && row.net_severity) || row.severity;
    flags.push({
      id: key,
      flag: true,
      kind: 'dosha',
      title,
      tag: `Flag · ${FLAG_WORD[severity] ?? severity}${met.length ? ' · Softened' : ''}`,
      tone: 'gold',
      what: reader.what ?? row.lay_explanation ?? '',
      why: row.why ?? [],
      impact: reader.impact ?? '',
      do: reader.do ?? [],
      avoid: reader.avoid ?? [],
      howCommon: reader.how_common ?? '',
      softens: met.map((e) => e.plain ?? e.detail),
      weakened: [],
      alsoChecked: exceptions.filter((e) => !e.applies).map((e) => e.plain ?? e.detail),
      classical: row.rule,
      triggers: [],
      convention: CONVENTION,
    });
  }
  return { flags, checked };
}

/**
 * Cards in reading order: strengths (strongest first), then flags, then one
 * closing list of what was checked and is not in the chart. Practitioner
 * also sees one-way Raja/Dhana links; Free sees two strengths in full and
 * every flag in full.
 */
export function buildCombinations(
  payload: YogasDoshasPayload | null,
  mode: ExperienceMode,
  allYogas: boolean,
): CombinationView {
  if (!payload) return { strengths: [], flags: [], checked: [], hiddenYogas: 0 };
  const active = (payload.yogas.active ?? []).filter((row) => mode === 'practitioner' || !row.partial);
  const goodRows = active.filter((row) => !isFlag(row));
  const flagRows = active.filter(isFlag);

  const groups = new Map<string, { items: Combination[]; rows: YogaResult[] }>();
  for (const row of goodRows) {
    const built = item(row, false);
    const group = groups.get(built.id) ?? { items: [], rows: [] };
    group.items.push(built);
    group.rows.push(row);
    groups.set(built.id, group);
  }
  let strengths = [...groups.values()]
    .map((group) => (group.items.length > 1 || GROUPED.has(group.rows[0].rule_id ?? '') ? merge(group.items, group.rows) : group.items[0]))
    .sort((a, b) => rank(b.tag) - rank(a.tag));
  let hiddenYogas = payload.yogas.locked_count ?? 0;
  if (!allYogas) {
    hiddenYogas += Math.max(0, strengths.length - FREE_YOGAS);
    strengths = strengths.slice(0, FREE_YOGAS);
  }

  const dosha = doshaItems(payload.doshas ?? null);
  const flags = [...dosha.flags, ...flagRows.map((row) => item(row, true))];
  const cancelled: CheckedRow[] = (payload.yogas.all ?? [])
    .filter((row) => row.cancelled)
    .map((row) => {
      const built = item(row, true);
      built.tag = 'Cancelled';
      built.tone = 'neutral';
      return { id: built.id, title: built.title, note: 'checked and cancelled', item: built };
    });
  return { strengths, flags, checked: [...cancelled, ...dosha.checked], hiddenYogas };
}

function rank(tag: string): number {
  return { Strong: 3, Medium: 2, Light: 1 }[tag] ?? 0;
}
