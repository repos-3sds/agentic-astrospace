export interface PlanetPosition {
  sign: string;
  degree: number;
  house: number;
  retrograde?: boolean;
}

export interface Kundli {
  id: string;
  user_id?: string;
  name: string;
  relation: string;
  notes?: string;
  sun_sign?: string;
  moon_sign?: string;
  ascendant?: string;
  birth_year: number;
  birth_month: number;
  birth_day: number;
  birth_hour: number;
  birth_minute: number;
  birth_city: string;
  birth_nation: string;
  chart_data?: {
    planets?: Record<string, PlanetPosition>;
    houses?: Record<string, { sign?: string; degree?: number }>;
  };
}

export interface KundliPayload {
  name: string;
  relation: string;
  birth_year: number;
  birth_month: number;
  birth_day: number;
  birth_hour: number;
  birth_minute: number;
  birth_city: string;
  birth_nation: string;
  notes?: string;
}

/* ── Vedic /all payload ─────────────────────────────────────────────── */

export interface VedicPlanet {
  longitude?: number;
  sign: string;
  sign_lord?: string;
  degree_in_sign?: number;
  dms: string;
  house: number;
  nakshatra: string;
  nakshatra_pada: number;
  nakshatra_lord?: string;
  retrograde?: boolean;
}

export interface VargaChart {
  name: string;
  signifies: string;
  verified_rule: boolean;
  provenance?: CalculationProvenance;
  lagna: { sign: string };
  planets: Record<
    string,
    { sign: string; sign_index?: number; house: number; retrograde?: boolean; vargottama?: boolean }
  >;
}

export interface CalculationProvenance {
  context: string;
  engine: string;
  zodiac: string;
  ayanamsha: string;
  node_type: string;
  house_system: string;
  lagna_method: string;
  timezone: string;
  calculation_place?: {
    city?: string;
    latitude?: number;
    longitude?: number;
  };
  panchanga_place?: { city: string; nation: string; timezone: string };
  confidence: Record<string, string>;
  notes: string[];
  [key: string]: unknown;
}

export type PlanetConditionCode = 'exalted' | 'debilitated' | 'retrograde' | 'combust' | 'vargottama';

export interface PlanetConditionAnnotation {
  code: PlanetConditionCode;
  symbol: string;
  label: string;
  tone: 'good' | 'bad' | 'neutral' | 'warn';
}

export interface VedicAll {
  meta: {
    birth_date: string;
    birth_time: string;
    weekday: string;
    place?: string;
    latitude: number;
    longitude: number;
    ayanamsha: { name: string; dms: string };
    sidereal_time: string;
    local_mean_time: string;
    node_type: string;
  };
  provenance?: CalculationProvenance;
  avkahada: Record<string, any>;
  ghatak: Record<string, any>;
  favourable: Record<string, any>;
  planets: Record<string, VedicPlanet>;
  dignities: Record<string, { dignity?: string }>;
  planetary_conditions?: PlanetaryConditionsPayload;
  planet_annotations?: Record<string, PlanetConditionAnnotation[]>;
  shadbala?: ShadbalaPayload;
  vargas: Record<string, VargaChart>;
  dashas?: DashaPayload;
  ashtakavarga?: AshtakavargaPayload;
  yogas?: YogasPayload;
  doshas?: DoshasPayload;
  jaimini?: JaiminiPayload;
  special_lagnas?: SpecialLagnasPayload;
  masa?: MasaPayload;
}

/* ── Jaimini payload ────────────────────────────────────────────────── */

export interface JaiminiKaraka {
  code?: string;
  planet: string;
  karaka: string;
  degree_in_sign: number;
  effective_degree: number;
  longitude: number;
}

export interface ArudhaPada {
  house: number;
  house_sign: number;
  house_sign_name: string;
  lord: string;
  lord_sign: number;
  lord_sign_name: string;
  count: number;
  raw_sign: number;
  raw_sign_name: string;
  exception_applied: boolean;
  sign: number;
  sign_name: string;
}

export interface JaiminiPayload {
  chara_karakas: {
    scheme: string;
    karakas: Record<string, JaiminiKaraka>;
    ordered: (JaiminiKaraka & { code: string })[];
  };
  arudha_lagna: ArudhaPada;
  upapada: ArudhaPada;
  arudha_padas: { padas: Record<string, ArudhaPada> };
}

export interface SpecialLagnaPoint {
  longitude: number;
  sign: number;
  sign_name: string;
  dms: string;
}

export interface SpecialLagnasPayload {
  hours_since_sunrise?: number;
  ghatis_since_sunrise?: number;
  bhava_lagna?: SpecialLagnaPoint;
  hora_lagna?: SpecialLagnaPoint;
  ghati_lagna?: SpecialLagnaPoint;
  lagna?: SpecialLagnaPoint;
  notes?: string[];
  error?: string;
}

/* ── Masa / Kaala payload ───────────────────────────────────────────── */

export interface DailyColorSwatch {
  name: string;
  hex: string;
  planet: string;
  source: string;
}

export interface DailyActionRow {
  text: string;
  source: string;
  window?: string;
}

export interface DailyGuidancePayload {
  system: string;
  as_of: string;
  date: string;
  subject: string;
  relation?: string;
  vara: string;
  verdict: {
    tone: 'supportive' | 'positive' | 'mixed' | 'caution';
    score: number;
    headline: string;
    text: string;
    word_count: number;
  };
  reading: {
    summary: string;
    focus: string;
    best_for: string[];
    avoid: string[];
    energy: 'low' | 'moderate' | 'steady' | 'high';
    relationship_tone: string;
    money_tone: string;
    work_tone: string;
    timing_note: string;
    plain_why: string[];
    technical_why: string[];
  };
  color: DailyColorSwatch & {
    power_color?: DailyColorSwatch;
    caution_color?: DailyColorSwatch;
  };
  number: {
    value: number;
    fit: 'favourable' | 'challenging' | 'neutral';
    ruling_planet: string;
    ruling_number: number;
    personal_good: number[];
    personal_evil: number[];
    source: string;
  };
  tarabala: { tara: string; count: number; favourable: boolean; note?: string | null };
  chandrabala: { house_from_rashi: number; favourable: boolean; chandrashtama: boolean };
  star_of_day: { nakshatra: string; moon_rashi: string; tithi: string };
  do_today: DailyActionRow[];
  avoid_today: DailyActionRow[];
  lucky_signature: {
    gem: string;
    metal: string;
    direction: string;
    days: string[];
  };
  lucky_numbers: {
    numerology: {
      number: number;
      ruling_planet: string;
      good_numbers: number[];
      evil_numbers: number[];
      source: string;
    };
    astrological: {
      number: number;
      planet: string;
      source: string;
      witnesses: { label: string; planet: string; number: number }[];
      confirmed_by: string[];
      confirmation_count: number;
    };
  };
  context: {
    route_domain: string;
    dasha_chain: { level: string; lord: string }[];
    references: { statement: string; source_text_key: string; source_location: string }[];
    active_gochara: { name: string; planet: string; severity?: string }[];
  };
  provenance: {
    engine: string;
    place: { city: string; nation: string; timezone: string };
    note: string;
  };
}

export interface MasaPayload {
  name: string;
  name_index: number;
  adhika: boolean;
  paksha: string;
  month_start_jd?: number;
  month_end_jd?: number;
  purnimanta_name?: string;
  samvatsara?: {
    name: string;
    index: number;
    number: number;
    shaka_year: number;
    source_status?: string;
  };
  ritu?: string;
  ayana?: string;
}

/* ── Yogini dasha payload ───────────────────────────────────────────── */

export interface YoginiDashaPeriod {
  yogini: string;
  planet: string;
  lord: string;
  start: string;
  end: string;
  years: number;
  active: boolean;
  antardashas?: YoginiDashaPeriod[];
}

export interface YoginiDashaPayload {
  system: string;
  cycle_years: number;
  birth_nakshatra: {
    name: string;
    number: number;
    starting_yogini: string;
    starting_planet: string;
    pada: number;
    elapsed_fraction: number;
    balance_years: number;
  };
  as_of: string;
  mahadashas: YoginiDashaPeriod[];
  current: {
    mahadasha?: YoginiDashaPeriod | null;
    antardasha?: YoginiDashaPeriod | null;
  };
}

export interface YogaResult {
  rule_id?: string;
  name: string;
  category: string;
  active: boolean;
  strength: string;
  rule: string;
  triggers: string[];
  planets: string[];
  verified: boolean;
  source_status?: 'verified_common' | 'convention_dependent' | 'needs_review' | string;
  implementation?: 'computed' | 'partial' | 'not_implemented' | string;
  source_refs?: { source: string; detail: string }[];
  notes?: string[];
}

export interface YogasPayload {
  lagna: string;
  total: number;
  active_count: number;
  active: YogaResult[];
  all: YogaResult[];
  categories: Record<string, number>;
  conventions?: Record<string, string>;
}

export interface ManglikException {
  rule: string;
  applies: boolean;
  detail: string;
  source_status?: string;
}

export interface ManglikPayload {
  rule_id?: string;
  name: string;
  active: boolean;
  severity: string;
  net_severity?: string;
  exceptions?: ManglikException[];
  active_references: string[];
  checks: {
    reference: string;
    house: number;
    active: boolean;
    mars_sign: string;
    reference_sign: string;
  }[];
  rule: string;
  verified: boolean;
  source_status?: 'verified_common' | 'convention_dependent' | 'needs_review' | string;
  implementation?: 'computed' | 'partial' | 'not_implemented' | string;
  source_refs?: { source: string; detail: string }[];
  notes?: string[];
}

export interface GandantaHit {
  body: string;
  junction: string;
  signs: string;
  side: string;
  degrees_from_junction: number;
  severity: string;
  abhukta_mula: boolean;
}

export interface GandantaPayload {
  rule_id?: string;
  name: string;
  active: boolean;
  severity: string;
  hits: GandantaHit[];
  bodies_checked?: string[];
  rule: string;
  verified: boolean;
  source_status?: string;
  implementation?: string;
  source_refs?: { source: string; detail: string }[];
  notes?: string[];
}

export interface GrahanHit {
  luminary: string;
  node: string;
  sign: string;
  orb: number;
  severity: string;
}

export interface GrahanPayload {
  rule_id?: string;
  name: string;
  active: boolean;
  severity: string;
  hits: GrahanHit[];
  rule: string;
  verified: boolean;
  source_status?: string;
  implementation?: string;
  source_refs?: { source: string; detail: string }[];
  notes?: string[];
}

export interface DoshasPayload {
  manglik: ManglikPayload;
  gandanta?: GandantaPayload;
  grahan?: GrahanPayload;
}

export interface YogasDoshasPayload {
  yogas: YogasPayload;
  doshas: DoshasPayload;
}

export interface DashaPeriod {
  lord: string;
  start: string;
  end: string;
  years: number;
  active: boolean;
  antardashas?: DashaPeriod[];
  pratyantardashas?: DashaPeriod[];
}

export interface DashaPayload {
  system: string;
  cycle_years: number;
  birth_nakshatra: {
    name: string;
    lord: string;
    pada: number;
    elapsed_fraction: number;
    balance_years: number;
  };
  as_of: string;
  mahadashas: DashaPeriod[];
  current: {
    mahadasha?: DashaPeriod | null;
    antardasha?: DashaPeriod | null;
    pratyantardasha?: DashaPeriod | null;
    pratyantardashas: DashaPeriod[];
    sookshmadasha?: DashaPeriod | null;
    sookshmadashas?: DashaPeriod[];
    pranadasha?: DashaPeriod | null;
    pranadashas?: DashaPeriod[];
  };
}

export interface AshtakavargaPayload {
  planets: string[];
  sources: string[];
  bav: Record<string, number[]>;
  source_breakdown?: Record<string, Record<string, number[]>>;
  prastara?: Record<string, Record<string, number[]>>;
  sav: number[];
  signs: {
    index: number;
    sign: string;
    sav: number;
    bav: Record<string, number>;
  }[];
  raw?: {
    bav: Record<string, number[]>;
    sav: number[];
    signs: AshtakavargaPayload['signs'];
  };
  shodhana?: Record<
    string,
    {
      trikona: number[];
      ekadhipatya: number[];
      total_after_trikona: number;
      total_after_ekadhipatya: number;
    }
  >;
  pinda?: Record<
    string,
    {
      rashi_pinda: number;
      graha_pinda: number;
      shodhya_pinda: number;
    }
  >;
  pinda_rank?: {
    planet: string;
    rashi_pinda: number;
    graha_pinda: number;
    shodhya_pinda: number;
  }[];
  totals: {
    bav: Record<string, number>;
    sav: number;
  };
}

export interface ShadbalaComponent {
  score: number;
  status: 'implemented' | 'approximation' | string;
  rule: string;
  [key: string]: unknown;
}

export interface ShadbalaClassicalComponent {
  virupas: number;
  sub?: Record<string, number>;
  [key: string]: unknown;
}

export interface ShadbalaClassicalRow {
  components: Record<string, ShadbalaClassicalComponent>;
  total_virupas: number;
  rupas: number;
  required_rupas: number;
  ratio: number;
  sufficient: boolean;
}

export interface ShadbalaClassicalPayload {
  system: string;
  scale: string;
  available: boolean;
  rows: Record<string, ShadbalaClassicalRow>;
  ranking: { planet: string; ratio: number; rupas: number; sufficient: boolean }[];
  required_minima_rupas?: Record<string, number>;
  day_context?: Record<string, unknown>;
  notes?: string[];
}

export interface ShadbalaPayload {
  system: string;
  scale: string;
  classical?: ShadbalaClassicalPayload;
  planets: string[];
  excluded: Record<string, string>;
  components: string[];
  weights: Record<string, number>;
  rows: Record<
    string,
    {
      total_score: number;
      base_score?: number;
      condition_modifier?: number;
      rank_band: 'strong' | 'moderate' | 'weak' | string;
      components: Record<string, ShadbalaComponent>;
      conditions?: PlanetaryConditionRow;
      notes: string[];
    }
  >;
  ranking: { planet: string; score: number; band: string }[];
  conditions?: PlanetaryConditionsPayload;
  provenance: { component: string; status: string; note: string }[];
}

export interface PlanetaryConditionRow {
  combustion: {
    active: boolean;
    severity: string;
    orb?: number | null;
    threshold?: number | null;
    modifier: number;
    status: string;
    rule: string;
  };
  avastha: {
    name: string;
    degree_in_sign: number;
    modifier: number;
    status: string;
    rule: string;
  };
  retrograde: {
    active: boolean;
    modifier: number;
    status: string;
    rule: string;
    speed: number;
  };
  planetary_war: {
    active: boolean;
    role: string;
    opponents: { planet: string; orb: number; result: string }[];
    modifier: number;
    status: string;
    rule: string;
  };
  net_modifier: number;
  provenance: { condition: string; status: string; note: string }[];
}

export interface PlanetaryConditionsPayload {
  system: string;
  rows: Record<string, PlanetaryConditionRow>;
  notes: string[];
}

export interface TransitContextPayload {
  as_of: {
    birth_date: string;
    birth_time: string;
    timezone: string;
  };
  provenance?: CalculationProvenance;
  planet_annotations?: {
    natal: Record<string, PlanetConditionAnnotation[]>;
    transit: Record<string, PlanetConditionAnnotation[]>;
  };
  natal: {
    rashi: VargaChart;
    navamsha: VargaChart;
  };
  transit: {
    rashi: VargaChart;
    navamsha: VargaChart;
  };
  gochara: Record<
    string,
    {
      sign: string;
      dms: string;
      nakshatra: string;
      nakshatra_pada: number;
      house_from_lagna: number;
      house_from_moon: number;
      retrograde?: boolean;
    }
  >;
  sade_sati: {
    active: boolean;
    phase?: string | null;
    saturn_house_from_moon: number;
  };
}

export interface TransitDignity {
  dignity: 'Exalted' | 'Moolatrikona' | 'Own' | 'Debilitated' | 'Neutral' | string;
  score: number;
  note?: string;
  dispositor?: string;
}

export interface TransitPlanetDetail {
  planet: string;
  longitude: number;
  sign: string;
  sign_index: number;
  degree_in_sign: number;
  dms: string;
  nakshatra: string;
  nakshatra_pada: number;
  house_from_lagna: number;
  house_from_moon: number;
  retrograde?: boolean;
  speed: number;
  /** US-GOC-017: the transiting planet's own dignity in its transit sign. */
  transit_dignity?: TransitDignity;
  /** US-GOC-017: houses this planet classically aspects from here (BPHS ch.3 graha-drishti). */
  special_aspect_houses_from_moon?: number[];
}

export interface ClassicalGocharaVedha {
  obstructed: boolean;
  by: string | null;
  vedha_house: number | null;
}

/** Phaladeepika ch.26 favourable-house/Vedha status for one transit planet. */
export interface ClassicalGocharaStatus {
  house_from_moon: number;
  favourable: boolean;
  vedha: ClassicalGocharaVedha;
  effective: 'favourable' | 'unfavourable' | 'obstructed' | string;
  source_status: 'classical_table' | 'convention_dependent' | string;
}

export interface TransitAspect {
  transit_planet: string;
  natal_planet: string;
  aspect: string;
  exact_angle: number;
  orb: number;
  strength: number;
  tone: 'neutral' | 'supportive' | 'challenging' | 'hard';
  transit_sign: string;
  natal_sign: string;
}

export interface AvContext {
  bindus: number;
  bav_support: string;
  sav: number;
  sav_support: string;
  kakshya?: {
    kakshya_index: number;
    kakshya_lord: string;
    bindu_given: boolean;
  };
}

export interface TransitRule {
  name: string;
  planet: string;
  active: boolean;
  severity: string;
  effective_severity?: string;
  av_context?: AvContext;
  trigger: string;
  note: string;
  explanation: string;
  verified: boolean;
}

export interface AshtakavargaTransitPlanet {
  planet: string;
  transit_sign: string;
  transit_sign_index: number;
  bindus: number;
  bav_support: string;
  sav: number;
  sav_support: string;
  kakshya?: {
    kakshya_index: number;
    kakshya_lord: string;
    bindu_given: boolean;
  } | null;
}

export interface AshtakavargaTransitPayload {
  planets: Record<string, AshtakavargaTransitPlanet>;
  note?: string;
}

export interface TransitTimelineEvent {
  date: string;
  type: 'sign_change' | 'aspect' | 'gochara_rule';
  planet: string;
  title: string;
  detail: string;
  tone: 'neutral' | 'supportive' | 'challenging' | 'hard';
  strength: number;
  aspect?: TransitAspect;
  rule?: string;
  transition?: string;
}

export interface GocharaPass {
  start: string | null;
  end: string | null;
  entry_type: 'first_entry' | 'retrograde_return' | 'final_exit' | 'continuing_before_horizon' | 'continuing_past_horizon' | string;
}

export interface GocharaActiveWindow {
  rule: string;
  rule_id?: string;
  planet: string;
  start_date?: string | null;
  end_date?: string | null;
  tone: 'neutral' | 'supportive' | 'challenging' | 'hard';
  trigger: string;
  summary: string;
  /** US-GOC-025: every pass through this window (Saturn long-cycle rules only, else null). */
  passes?: GocharaPass[] | null;
}

export interface GocharaRuleTimeline {
  active_windows: GocharaActiveWindow[];
  previous_365_days: TransitTimelineEvent[];
  next_365_days: TransitTimelineEvent[];
  scan_days: number;
}

export interface GocharaCoreReadingBlock {
  title: string;
  tone: 'neutral' | 'supportive' | 'challenging' | 'hard' | 'mixed';
  rationale: string;
  reading: string;
  timing_summary: string;
}

export interface GocharamPeriod extends GocharaActiveWindow {
  rule_id: string;
  start_date: string;
  status: 'past' | 'current' | 'future' | string;
  strength: number;
  rationale: string;
  reading: string;
  validation_prompt: string;
}

export interface GocharamRuleContent {
  guided_summary: string;
  balanced_context: string;
  practitioner_deep_dive: string;
}

export interface GocharamMatchedRule {
  rule_id: string;
  kind: 'baseline_placement' | 'special_overlay' | string;
  rule_name: string;
  planet: string;
  anchor: string;
  house: number;
  category: string;
  duration: string;
  base_verdict: 'supportive' | 'challenging' | 'neutral';
  effective_verdict: 'supportive' | 'challenging' | 'mixed' | 'neutral';
  source_id: string;
  source_status: string;
  claim_status: string;
  content: GocharamRuleContent;
  modifiers: Array<{
    type: 'vedha' | 'ashtakavarga' | 'motion' | 'natal_contact' | 'dasha_concordance' | 'timing' | string;
    effect: string;
    label: string;
    evidence: Record<string, unknown>;
  }>;
}

export interface GocharamRangeOutlook {
  days: number;
  event_count: number;
  previous_event_count: number;
  supportive_count: number;
  challenging_count: number;
  tone: 'neutral' | 'supportive' | 'challenging' | 'mixed';
  title: string;
  reading: string;
  previous_title: string;
  previous_reading: string;
  first_change?: TransitTimelineEvent | null;
  last_change?: TransitTimelineEvent | null;
  highlights: TransitTimelineEvent[];
  previous_highlights: TransitTimelineEvent[];
}

export interface GocharamDomainReading {
  id: 'career' | 'money' | 'relationships' | 'health_energy' | 'learning_travel' | 'inner_life' | string;
  title: string;
  tone: 'neutral' | 'supportive' | 'challenging' | 'mixed';
  main_theme: string;
  rationale: string;
  reading: string;
  strengths: string[];
  challenges: string[];
  actions: string[];
  leading_planets: string[];
  evidence_ids: string[];
  range_outlook: GocharamRangeOutlook;
}

export interface GocharamInterpretation {
  schema_version: string;
  library_version: string;
  mode: string;
  methodology: {
    calculation_rule: string;
    interpretation_rule: string;
  };
  convention: {
    primary_anchor?: string;
    ayanamsha?: string;
    node_treatment?: string;
    safety?: string;
  };
  sources: Array<{
    id: string;
    work: string;
    location: string;
    scope: string;
    edition_status: string;
  }>;
  synthesis: {
    tone: 'supportive' | 'challenging' | 'mixed' | 'neutral';
    headline: string;
    counts: { supportive: number; mixed: number; challenging: number };
    guided_summary: string;
    balanced_context: string;
    practitioner_deep_dive: string;
  };
  range_outlook: GocharamRangeOutlook;
  domains: GocharamDomainReading[];
  matched_rules: GocharamMatchedRule[];
  evidence: Array<Record<string, unknown>>;
}

export interface GocharamProfilePayload {
  schema_version: string;
  engine_version: string;
  system: string;
  as_of: string;
  ayanamsha: string;
  node_type: string;
  natal: {
    lagna_sign: string;
    moon_sign: string;
  };
  gochara: TransitAnalysisPayload['gochara'];
  ashtakavarga_transit?: AshtakavargaTransitPayload;
  periods: GocharamPeriod[];
  coverage: {
    past_days: number;
    future_days: number;
    strategy: string;
  };
  notes: string[];
}

export interface TransitAnalysisPayload {
  system: string;
  as_of: string;
  ayanamsha: string;
  node_type: string;
  natal: {
    lagna_sign: string;
    moon_sign: string;
  };
  gochara: {
    planets: Record<string, TransitPlanetDetail>;
    rules: TransitRule[];
    active_rules: TransitRule[];
    core_reading: {
      title: string;
      tone: 'neutral' | 'supportive' | 'challenging' | 'mixed';
      rationale: string;
      reading: string;
      timing_summary: string;
      next: GocharaCoreReadingBlock;
      previous: GocharaCoreReadingBlock;
      sentences?: string[];
      active_rule_count: number;
      supportive_rule_count: number;
      challenging_rule_count: number;
    };
    timeline: GocharaRuleTimeline;
    interpretation: GocharamInterpretation;
    sade_sati: {
      active: boolean;
      phase?: string | null;
      saturn_house_from_moon: number;
    };
    /** Phaladeepika ch.26 favourable/Vedha status per transit planet. */
    classical_gochara?: Record<string, ClassicalGocharaStatus>;
    /** Same object as the top-level ashtakavarga_transit, mirrored here by the backend. */
    ashtakavarga?: AshtakavargaTransitPayload;
  };
  gocharam_periods?: GocharamPeriod[];
  gocharam_coverage?: GocharamProfilePayload['coverage'];
  ashtakavarga_transit?: AshtakavargaTransitPayload;
  aspects: TransitAspect[];
  active_aspects: TransitAspect[];
  strongest_aspect?: TransitAspect | null;
  timeline: {
    next_7_days: TransitTimelineEvent[];
    next_30_days: TransitTimelineEvent[];
  };
  notes: string[];
}

export interface CalendarEvent {
  date: string;
  category: 'dasha' | 'panchanga' | 'transit' | string;
  title: string;
  detail: string;
  tone: 'neutral' | 'supportive' | 'challenging' | 'hard' | string;
  strength: number;
  meta?: Record<string, unknown>;
}

export interface FestivalOccurrence {
  slug: string;
  name: string;
  local_names?: Record<string, string>;
  regions: string[];
  description?: string | null;
  prep_guidance?: string | null;
  occurs_on: string;
  observance_note?: string | null;
  is_convention_dependent?: boolean;
}

export interface FestivalWindowPayload {
  from_date: string;
  to_date: string;
  place: { city: string; nation: string };
  count: number;
  festivals: FestivalOccurrence[];
}

export interface CalendarDaySummary {
  date: string;
  vara: string;
  tithi: string;
  nakshatra: string;
  moon_rashi: string;
  tarabala: { tara: string; count: number; favourable: boolean; note?: string | null };
  chandrabala: { house_from_rashi: number; favourable: boolean; chandrashtama: boolean };
  auspicious_count: number;
  inauspicious_count: number;
  windows: {
    auspicious: PanchangaWindow[];
    inauspicious: PanchangaWindow[];
  };
}

export interface CalendarReadingMarker {
  id: string;
  reading_type: string;
  period_label?: string;
  generated_local_date?: string;
  version: number;
  deviation_score?: number;
  deviation_band?: string;
  user_rating?: number;
  feedback_status: string;
  reviewed_at?: string;
  generated_at?: string;
}

export interface CalendarIntelligencePayload {
  system: string;
  profile: { name: string; janma_nakshatra: string };
  provenance?: CalculationProvenance;
  start_date: string;
  end_date: string;
  timezone: string;
  place: { city: string; nation: string; timezone: string };
  current: {
    dasha: DashaPayload['current'];
    strongest_transit?: TransitAspect | null;
    active_rules: TransitRule[];
    panchanga?: CalendarDaySummary | null;
    readings?: CalendarReadingMarker[];
    prediction_claims?: PredictionClaim[];
  };
  panchanga_days: CalendarDaySummary[];
  events: CalendarEvent[];
  by_date: Record<string, CalendarEvent[]>;
  readings_by_date?: Record<string, CalendarReadingMarker[]>;
  prediction_claims_by_date?: Record<string, PredictionClaim[]>;
  notes: string[];
}

/* ── Panchanga /today payload ───────────────────────────────────────── */

export interface PanchangaEntry {
  name: string;
  upto: string;
}

export interface PanchangaWindow {
  name: string;
  start: string;
  end: string;
  start_iso: string;
  end_iso: string;
  note?: string;
}

export interface PanchangaDay {
  date: string;
  place: { city: string; timezone?: string; calculation_timezone?: string; nation?: string };
  vara: { name: string };
  sunrise: string;
  sunset: string;
  next_sunrise: string;
  moon_rashi_at_sunrise: string;
  elements: {
    tithi: PanchangaEntry[];
    nakshatra: PanchangaEntry[];
    yoga: PanchangaEntry[];
    karana: PanchangaEntry[];
  };
  windows: {
    auspicious: PanchangaWindow[];
    inauspicious: PanchangaWindow[];
  };
  choghadiya: {
    day: { name: string; kind: 'good' | 'bad' | 'neutral'; start: string }[];
  };
  personal?: {
    janma: { nakshatra: string; rashi: string };
    tarabala: { tara: string; count: number; favourable: boolean };
    chandrabala: { favourable: boolean; chandrashtama: boolean; house_from_rashi: number };
    ghatak_alerts: { matched: boolean; type: string; ghatak_value: unknown }[];
  };
}

export interface PanchangaCity {
  city: string;
  nation: string;
  timezone: string;
  lat: number;
  lng: number;
  label: string;
}

export interface CompatibilityScoreRow {
  label: string;
  points: number;
  max: number;
  note: string;
  verified?: boolean;
}

export interface CompatibilityPayload {
  system: string;
  total: number;
  max: number;
  percent: number;
  verdict: string;
  rows: CompatibilityScoreRow[];
  notes?: string[];
  profiles?: Record<string, unknown>;
}

/* ── AI payloads ────────────────────────────────────────────────────── */

export interface Reading {
  id: string;
  kundli_id: string;
  reading_type: string;
  period_label?: string;
  content: string;
  cached?: boolean;
  generated_at?: string;
  generated_local_date?: string;
  version?: number;
  parent_reading_id?: string;
  deviation_score?: number;
  deviation_summary?: {
    band?: string;
    similarity?: number;
    added_terms?: string[];
    removed_terms?: string[];
  };
  user_rating?: number;
  user_feedback?: string;
  reviewed_at?: string;
}

export type PredictionClaimStatus = 'pending' | 'accurate' | 'partly' | 'missed' | 'not_applicable';

export interface PredictionClaim {
  id: string;
  kundli_id: string;
  reading_id: string;
  reading_type: string;
  period_label?: string;
  generated_local_date?: string;
  target_start_date?: string;
  target_end_date?: string;
  category: string;
  claim_text: string;
  confidence?: number;
  source_excerpt?: string;
  status: PredictionClaimStatus;
  user_feedback?: string;
  reviewed_at?: string;
  created_at?: string;
}

export interface AskMessage {
  role: 'user' | 'assistant';
  content: string;
  tools?: string[];
}

export interface AskResponse {
  answer: string;
  tools_used: string[];
  kundli_id?: string;
  thread_id?: string | null;
  refer_out_kind?: 'health' | 'legal' | 'money' | 'death' | null;
}
