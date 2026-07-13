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
  lagna: { sign: string };
  planets: Record<
    string,
    { sign: string; sign_index?: number; house: number; retrograde?: boolean; vargottama?: boolean }
  >;
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
  avkahada: Record<string, any>;
  ghatak: Record<string, any>;
  favourable: Record<string, any>;
  planets: Record<string, VedicPlanet>;
  dignities: Record<string, { dignity?: string }>;
  planetary_conditions?: PlanetaryConditionsPayload;
  shadbala?: ShadbalaPayload;
  vargas: Record<string, VargaChart>;
  dashas?: DashaPayload;
  ashtakavarga?: AshtakavargaPayload;
  yogas?: YogasPayload;
  doshas?: DoshasPayload;
}

export interface YogaResult {
  name: string;
  category: string;
  active: boolean;
  strength: string;
  rule: string;
  triggers: string[];
  planets: string[];
  verified: boolean;
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

export interface ManglikPayload {
  name: string;
  active: boolean;
  severity: string;
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
  notes?: string[];
}

export interface DoshasPayload {
  manglik: ManglikPayload;
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

export interface ShadbalaPayload {
  system: string;
  scale: string;
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

export interface TransitRule {
  name: string;
  planet: string;
  active: boolean;
  severity: string;
  trigger: string;
  note: string;
  verified: boolean;
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
    sade_sati: {
      active: boolean;
      phase?: string | null;
      saturn_house_from_moon: number;
    };
  };
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
}
