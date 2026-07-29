import { expect, test, type Page, type Route } from '@playwright/test';

const profileOne = {
  id: 'profile-1',
  name: 'Anika Rao',
  relation: 'self',
  sun_sign: 'Leo',
  moon_sign: 'Cancer',
  ascendant: 'Libra',
  birth_year: 1992,
  birth_month: 8,
  birth_day: 12,
  birth_hour: 9,
  birth_minute: 30,
  birth_city: 'Mumbai',
  birth_nation: 'IN',
};

const profileTwo = {
  id: 'profile-2',
  name: 'Ravi Rao',
  relation: 'partner',
  sun_sign: 'Gemini',
  moon_sign: 'Virgo',
  ascendant: 'Sagittarius',
  birth_year: 1991,
  birth_month: 3,
  birth_day: 4,
  birth_hour: 7,
  birth_minute: 10,
  birth_city: 'Hyderabad',
  birth_nation: 'IN',
};

function phoneOnly(projectName: string): void {
  test.skip(projectName !== 'mobile-chrome-360', 'One phone project covers these stateful mobile flows');
}

async function mockMobileApi(page: Page): Promise<{
  profiles: Record<string, unknown>[];
  claims: Record<string, unknown>[];
}> {
  const state = {
    profiles: [{ ...profileOne }, { ...profileTwo }] as Record<string, unknown>[],
    alertsFailedOnce: false,
    claims: [
      {
        id: 'claim-1',
        kundli_id: 'profile-1',
        reading_id: 'reading-1',
        reading_type: 'weekly',
        category: 'career',
        claim_text: 'A practical work conversation needs follow-up.',
        status: 'accurate',
        target_start_date: '2026-07-27',
        target_end_date: '2026-07-31',
      },
      {
        id: 'claim-2',
        kundli_id: 'profile-1',
        reading_id: 'reading-1',
        reading_type: 'weekly',
        category: 'health',
        claim_text: 'Energy returns after mid-week.',
        status: 'missed',
        target_start_date: '2026-07-29',
      },
      {
        id: 'claim-3',
        kundli_id: 'profile-1',
        reading_id: 'reading-1',
        reading_type: 'weekly',
        category: 'wealth',
        claim_text: 'A delayed payment clears before the weekend.',
        status: 'pending',
        target_start_date: '2026-07-30',
      },
    ] as Record<string, unknown>[],
  };

  const calendarPayload = {
    system: 'Lahiri',
    profile: { name: 'Anika Rao', janma_nakshatra: 'Rohini' },
    start_date: '2026-07-28',
    end_date: '2026-08-15',
    timezone: 'Asia/Kolkata',
    place: { city: 'Mumbai', nation: 'IN', timezone: 'Asia/Kolkata' },
    current: {
      dasha: {
        mahadasha: { lord: 'Venus' },
        antardasha: { lord: 'Saturn' },
        pratyantardasha: { lord: 'Mercury' },
      },
      active_rules: [],
      strongest_transit: null,
      panchanga: null,
      readings: [],
      prediction_claims: [],
    },
    panchanga_days: [
      {
        date: '2026-07-28',
        vara: 'Tuesday',
        tithi: 'Dashami',
        nakshatra: 'Krittika',
        moon_rashi: 'Taurus',
        tarabala: { tara: 'Sampat', count: 2, favourable: true },
        chandrabala: { house_from_rashi: 11, favourable: true, chandrashtama: false },
        auspicious_count: 1,
        inauspicious_count: 1,
        windows: {
          auspicious: [{ name: 'Amrit Kalam', start: '09:10', end: '10:20', start_iso: '2026-07-28T09:10:00+05:30', end_iso: '2026-07-28T10:20:00+05:30' }],
          inauspicious: [{ name: 'Rahu Kalam', start: '15:30', end: '17:00', start_iso: '2026-07-28T15:30:00+05:30', end_iso: '2026-07-28T17:00:00+05:30' }],
        },
      },
      {
        date: '2026-07-29',
        vara: 'Wednesday',
        tithi: 'Ekadashi',
        nakshatra: 'Rohini',
        moon_rashi: 'Taurus',
        tarabala: { tara: 'Janma', count: 1, favourable: false },
        chandrabala: { house_from_rashi: 11, favourable: true, chandrashtama: false },
        auspicious_count: 1,
        inauspicious_count: 0,
        windows: {
          auspicious: [{ name: 'Abhijit Muhurta', start: '12:05', end: '12:55', start_iso: '2026-07-29T12:05:00+05:30', end_iso: '2026-07-29T12:55:00+05:30' }],
          inauspicious: [],
        },
      },
      {
        date: '2026-08-01',
        vara: 'Saturday',
        tithi: 'Trayodashi',
        nakshatra: 'Mrigashira',
        moon_rashi: 'Gemini',
        tarabala: { tara: 'Kshema', count: 4, favourable: true },
        chandrabala: { house_from_rashi: 12, favourable: false, chandrashtama: false },
        auspicious_count: 0,
        inauspicious_count: 1,
        windows: { auspicious: [], inauspicious: [] },
      },
    ],
    events: [
      { date: '2026-07-29', category: 'transit', title: 'API transit opening', detail: 'Mercury supports follow-up calls.', tone: 'supportive', strength: 82 },
      { date: '2026-08-01', category: 'dasha', title: 'August focus', detail: 'Saturn antar asks for slow planning.', tone: 'neutral', strength: 55 },
    ],
    by_date: {
      '2026-07-29': [{ date: '2026-07-29', category: 'transit', title: 'API transit opening', detail: 'Mercury supports follow-up calls.', tone: 'supportive', strength: 82 }],
      '2026-08-01': [{ date: '2026-08-01', category: 'dasha', title: 'August focus', detail: 'Saturn antar asks for slow planning.', tone: 'neutral', strength: 55 }],
    },
    readings_by_date: {},
    prediction_claims_by_date: {},
    notes: [],
  };

  const compatibilityPayload = (partnerName: string) => ({
    system: 'Lahiri',
    total: partnerName === 'Nisha Kapoor' ? 31 : 28,
    max: 36,
    percent: partnerName === 'Nisha Kapoor' ? 86 : 78,
    verdict: partnerName === 'Nisha Kapoor' ? 'API high-support match' : 'API workable match',
    rows: [
      { label: 'Nadi', points: 8, max: 8, note: 'Nadi matched from API' },
      { label: 'Bhakoot', points: 7, max: 7, note: 'Moon-sign distance returned by API' },
      { label: 'Gana', points: 5, max: 6, note: `${partnerName} adds steady emotional texture.` },
      { label: 'Tara', points: 3, max: 3, note: 'Nakshatra support is favorable.' },
      { label: 'Yoni', points: 5, max: 6, note: 'Physical temperament is mostly aligned.' },
    ],
    notes: ['Backend compatibility note.'],
  });

  const vedicAllPayload = {
    meta: {
      birth_date: '1992-08-12',
      birth_time: '09:30',
      weekday: 'Wednesday',
      place: 'Mumbai, IN',
      latitude: 19.076,
      longitude: 72.8777,
      ayanamsha: { name: 'Lahiri', dms: '24° 08′' },
      sidereal_time: '10:22:11',
      local_mean_time: '09:09',
      node_type: 'mean',
    },
    provenance: {
      context: 'e2e',
      engine: 'Mock Swiss Ephemeris',
      zodiac: 'sidereal',
      ayanamsha: 'Lahiri',
      node_type: 'mean',
      house_system: 'whole-sign',
      lagna_method: 'rashi',
      timezone: 'Asia/Kolkata',
      calculation_place: { city: 'Mumbai', latitude: 19.076, longitude: 72.8777 },
      confidence: { birth_time: 'provided' },
      notes: [],
    },
    avkahada: {},
    ghatak: {},
    favourable: {},
    planets: {
      Sun: { longitude: 12, sign: 'Aries', degree_in_sign: 12, dms: '12° 00′', house: 10, nakshatra: 'Ashwini', nakshatra_pada: 4 },
      Moon: { longitude: 49, sign: 'Taurus', degree_in_sign: 19, dms: '19° 00′', house: 11, nakshatra: 'Rohini', nakshatra_pada: 3 },
      Mars: { longitude: 101, sign: 'Cancer', degree_in_sign: 11, dms: '11° 00′', house: 12, nakshatra: 'Pushya', nakshatra_pada: 3 },
      Mercury: { longitude: 205, sign: 'Libra', degree_in_sign: 25, dms: '25° 00′', house: 4, nakshatra: 'Vishakha', nakshatra_pada: 2 },
      Jupiter: { longitude: 250, sign: 'Sagittarius', degree_in_sign: 10, dms: '10° 00′', house: 6, nakshatra: 'Mula', nakshatra_pada: 4 },
      Venus: { longitude: 330, sign: 'Pisces', degree_in_sign: 0, dms: '00° 20′', house: 9, nakshatra: 'Purva Bhadrapada', nakshatra_pada: 4 },
      Saturn: { longitude: 280, sign: 'Capricorn', degree_in_sign: 10, dms: '10° 00′', house: 7, nakshatra: 'Shravana', nakshatra_pada: 1, retrograde: true },
      Rahu: { longitude: 60, sign: 'Gemini', degree_in_sign: 0, dms: '00° 00′', house: 12, nakshatra: 'Mrigashira', nakshatra_pada: 3 },
      Ketu: { longitude: 240, sign: 'Sagittarius', degree_in_sign: 0, dms: '00° 00′', house: 6, nakshatra: 'Mula', nakshatra_pada: 1 },
    },
    dignities: {},
    vargas: {
      D1: {
        name: 'Rashi',
        signifies: 'Self and life path',
        verified_rule: true,
        lagna: { sign: 'Cancer' },
        planets: {
          Sun: { sign: 'Aries', house: 10 },
          Moon: { sign: 'Taurus', house: 11 },
          Mars: { sign: 'Cancer', house: 1 },
          Mercury: { sign: 'Libra', house: 4 },
          Jupiter: { sign: 'Sagittarius', house: 6 },
          Venus: { sign: 'Pisces', house: 9 },
          Saturn: { sign: 'Capricorn', house: 7, retrograde: true },
          Rahu: { sign: 'Gemini', house: 12 },
          Ketu: { sign: 'Sagittarius', house: 6 },
        },
      },
      D9: {
        name: 'Navamsha',
        signifies: 'Marriage and dharma',
        verified_rule: true,
        lagna: { sign: 'Leo' },
        planets: {
          Sun: { sign: 'Scorpio', house: 4 },
          Moon: { sign: 'Taurus', house: 10, vargottama: true },
          Mars: { sign: 'Virgo', house: 2 },
          Mercury: { sign: 'Aquarius', house: 7 },
          Jupiter: { sign: 'Pisces', house: 8 },
          Venus: { sign: 'Cancer', house: 12 },
          Saturn: { sign: 'Libra', house: 3 },
          Rahu: { sign: 'Aries', house: 9 },
          Ketu: { sign: 'Libra', house: 3 },
        },
      },
      D10: {
        name: 'Dashamsha',
        signifies: 'Career and public work',
        verified_rule: true,
        lagna: { sign: 'Virgo' },
        planets: {
          Sun: { sign: 'Leo', house: 12 },
          Moon: { sign: 'Gemini', house: 10 },
          Mars: { sign: 'Capricorn', house: 5 },
          Mercury: { sign: 'Virgo', house: 1 },
          Jupiter: { sign: 'Sagittarius', house: 4 },
          Venus: { sign: 'Libra', house: 2 },
          Saturn: { sign: 'Aquarius', house: 6 },
          Rahu: { sign: 'Taurus', house: 9 },
          Ketu: { sign: 'Scorpio', house: 3 },
        },
      },
    },
    ashtakavarga: {
      planets: ['Sun', 'Moon', 'Mars'],
      sources: ['mock'],
      bav: { Sun: [5, 3, 2, 4, 6, 1, 3, 4, 5, 2, 3, 4], Moon: [3, 4, 4, 5, 2, 2, 4, 5, 3, 4, 2, 1], Mars: [2, 2, 5, 3, 4, 3, 5, 2, 4, 4, 3, 1] },
      sav: [31, 27, 24, 30, 33, 22, 29, 31, 28, 26, 25, 21],
      signs: [],
      totals: { bav: { Sun: 42, Moon: 39, Mars: 38 }, sav: 327 },
    },
    shadbala: {
      system: 'mock',
      scale: 'ratio',
      planets: ['Sun', 'Moon'],
      excluded: {},
      components: [],
      weights: {},
      rows: {},
      ranking: [{ planet: 'Sun', score: 118, band: 'strong' }, { planet: 'Moon', score: 84, band: 'moderate' }],
      classical: {
        system: 'mock',
        scale: 'rupas',
        available: true,
        rows: {},
        ranking: [{ planet: 'Sun', ratio: 1.18, rupas: 7.1, sufficient: true }, { planet: 'Moon', ratio: 0.84, rupas: 4.2, sufficient: false }],
        required_minima_rupas: { Sun: 6, Moon: 5 },
      },
      provenance: [],
    },
    jaimini: {
      chara_karakas: {
        scheme: '7-karaka',
        karakas: {},
        ordered: [
          { code: 'AK', planet: 'Saturn', karaka: 'Atmakaraka', degree_in_sign: 27.4, effective_degree: 27.4, longitude: 297.4 },
          { code: 'AmK', planet: 'Jupiter', karaka: 'Amatyakaraka', degree_in_sign: 24.1, effective_degree: 24.1, longitude: 264.1 },
        ],
      },
      arudha_lagna: { house: 1, house_sign: 4, house_sign_name: 'Cancer', lord: 'Moon', lord_sign: 2, lord_sign_name: 'Taurus', count: 11, raw_sign: 12, raw_sign_name: 'Pisces', exception_applied: false, sign: 12, sign_name: 'Pisces' },
      upapada: { house: 12, house_sign: 3, house_sign_name: 'Gemini', lord: 'Mercury', lord_sign: 7, lord_sign_name: 'Libra', count: 5, raw_sign: 8, raw_sign_name: 'Scorpio', exception_applied: false, sign: 8, sign_name: 'Scorpio' },
      arudha_padas: { padas: { A10: { house: 10, house_sign: 1, house_sign_name: 'Aries', lord: 'Mars', lord_sign: 4, lord_sign_name: 'Cancer', count: 4, raw_sign: 5, raw_sign_name: 'Leo', exception_applied: false, sign: 5, sign_name: 'Leo' } } },
    },
    special_lagnas: {
      bhava_lagna: { longitude: 95, sign: 4, sign_name: 'Cancer', dms: '05° 00′' },
      hora_lagna: { longitude: 185, sign: 7, sign_name: 'Libra', dms: '05° 00′' },
      ghati_lagna: { longitude: 275, sign: 10, sign_name: 'Capricorn', dms: '05° 00′' },
    },
  };

  const dashaPayload = {
    system: 'Vimshottari',
    cycle_years: 120,
    birth_nakshatra: { name: 'Rohini', lord: 'Moon', pada: 3, elapsed_fraction: 0.4, balance_years: 6 },
    as_of: '2026-07-28',
    mahadashas: [
      { lord: 'Moon', start: '2018-01-01', end: '2028-01-01', years: 10, active: true, antardashas: [
        { lord: 'Saturn', start: '2025-01-01', end: '2026-08-01', years: 1.6, active: true, pratyantardashas: [
          { lord: 'Mercury', start: '2026-05-01', end: '2026-08-01', years: 0.25, active: true },
        ] },
      ] },
      { lord: 'Mars', start: '2028-01-01', end: '2035-01-01', years: 7, active: false },
    ],
    current: {
      mahadasha: { lord: 'Moon', start: '2018-01-01', end: '2028-01-01', years: 10, active: true },
      antardasha: { lord: 'Saturn', start: '2025-01-01', end: '2026-08-01', years: 1.6, active: true },
      pratyantardasha: { lord: 'Mercury', start: '2026-05-01', end: '2026-08-01', years: 0.25, active: true },
      pratyantardashas: [{ lord: 'Mercury', start: '2026-05-01', end: '2026-08-01', years: 0.25, active: true }],
    },
  };

  const yoginiPayload = {
    system: 'Yogini',
    cycle_years: 36,
    birth_nakshatra: { name: 'Rohini', number: 4, starting_yogini: 'Pingala', starting_planet: 'Sun', pada: 3, elapsed_fraction: 0.2, balance_years: 1 },
    as_of: '2026-07-28',
    mahadashas: [{ yogini: 'Dhanya', planet: 'Jupiter', lord: 'Dhanya', start: '2022-01-01', end: '2027-01-01', years: 5, active: true }],
    current: { mahadasha: { yogini: 'Dhanya', planet: 'Jupiter', lord: 'Dhanya', start: '2022-01-01', end: '2027-01-01', years: 5, active: true } },
  };

  const yogasDoshasPayload = {
    yogas: {
      lagna: 'Cancer',
      total: 1,
      active_count: 1,
      active: [{ rule_id: 'api-yoga', name: 'API Chandra-Mangala Yoga', category: 'wealth', active: true, strength: 'strong', rule: 'Moon and Mars relationship returned by API.', triggers: ['Moon', 'Mars'], planets: ['Moon', 'Mars'], verified: true, source_status: 'verified_common', implementation: 'computed' }],
      all: [],
      categories: { wealth: 1 },
    },
    doshas: {
      manglik: { name: 'API Manglik Check', active: false, severity: 'none', active_references: [], checks: [], rule: 'Mars check returned by API.', verified: true, source_status: 'verified_common', implementation: 'computed', exceptions: [] },
    },
  };

  await page.route('**/api/v1/**', async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (url.pathname === '/api/v1/auth/config') {
      await route.fulfill({ json: { enabled: false } });
      return;
    }

    if (url.pathname === '/api/v1/kundlis' && request.method() === 'GET') {
      await route.fulfill({ json: state.profiles });
      return;
    }

    if (url.pathname === '/api/v1/me/alerts' && request.method() === 'GET') {
      if (!state.alertsFailedOnce) {
        state.alertsFailedOnce = true;
        await route.fulfill({ status: 503, json: { detail: 'temporary alerts outage' } });
        return;
      }
      await route.fulfill({
        json: {
          alerts: [
            {
              id: 'alert-1',
              category: 'transit',
              title: 'API transit alert',
              body: 'Mercury is changing signs.',
              deep_link: '/m/transits',
              read_at: null,
              created_at: '2026-07-28T08:00:00Z',
            },
          ],
        },
      });
      return;
    }

    if (url.pathname === '/api/v1/me/alerts/alert-1/read' && request.method() === 'POST') {
      await route.fulfill({ status: 204, body: '' });
      return;
    }

    if (url.pathname === '/api/v1/kundlis' && request.method() === 'POST') {
      const created = {
        id: 'profile-3',
        ...request.postDataJSON(),
        sun_sign: 'Taurus',
        moon_sign: 'Scorpio',
        ascendant: 'Cancer',
      };
      state.profiles.push(created);
      await route.fulfill({ status: 201, json: created });
      return;
    }

    const kundliMatch = url.pathname.match(/^\/api\/v1\/kundlis\/([^/]+)$/);
    if (kundliMatch && request.method() === 'PATCH') {
      const id = kundliMatch[1];
      const body = request.postDataJSON();
      const index = state.profiles.findIndex((profile) => profile['id'] === id);
      if (index >= 0) state.profiles[index] = { ...state.profiles[index], ...body };
      await route.fulfill({ json: state.profiles[index] });
      return;
    }

    if (kundliMatch && request.method() === 'DELETE') {
      const id = kundliMatch[1];
      state.profiles = state.profiles.filter((profile) => profile['id'] !== id);
      await route.fulfill({ status: 204, body: '' });
      return;
    }

    if (url.pathname === '/api/v1/readings/profile-1' && request.method() === 'GET') {
      await route.fulfill({
        json: [
          {
            id: 'reading-1',
            kundli_id: 'profile-1',
            reading_type: url.searchParams.get('period') ?? 'weekly',
            period_label: 'Week of 27 July 2026',
            content: 'Mercury week reading from the API.',
            generated_at: '2026-07-27T08:00:00Z',
            generated_local_date: '2026-07-27',
            version: 4,
          },
        ],
      });
      return;
    }

    if (url.pathname === '/api/v1/readings/profile-1/claims' && request.method() === 'GET') {
      await route.fulfill({ json: state.claims });
      return;
    }

    if (url.pathname === '/api/v1/vedic/profile-1/calendar-intelligence' && request.method() === 'GET') {
      await route.fulfill({ json: calendarPayload });
      return;
    }

    if (url.pathname === '/api/v1/vedic/profile-1/all' && request.method() === 'GET') {
      await route.fulfill({ json: vedicAllPayload });
      return;
    }

    if (url.pathname === '/api/v1/vedic/profile-1/dashas' && request.method() === 'GET') {
      await route.fulfill({ json: dashaPayload });
      return;
    }

    if (url.pathname === '/api/v1/vedic/profile-1/yogini-dashas' && request.method() === 'GET') {
      await route.fulfill({ json: yoginiPayload });
      return;
    }

    if (url.pathname === '/api/v1/vedic/profile-1/yogas-doshas' && request.method() === 'GET') {
      await route.fulfill({ json: yogasDoshasPayload });
      return;
    }

    if (url.pathname === '/api/v1/vedic/profile-1/ashtakavarga' && request.method() === 'GET') {
      await route.fulfill({ json: vedicAllPayload.ashtakavarga });
      return;
    }

    if (url.pathname === '/api/v1/vedic/profile-1/compatibility/profile-2' && request.method() === 'GET') {
      await route.fulfill({ json: compatibilityPayload('Ravi Rao') });
      return;
    }

    if (url.pathname === '/api/v1/vedic/profile-1/compatibility/profile-3' && request.method() === 'GET') {
      await route.fulfill({ json: compatibilityPayload('Nisha Kapoor') });
      return;
    }

    if (url.pathname === '/api/v1/readings/profile-1/generate' && request.method() === 'POST') {
      await route.fulfill({
        status: 201,
        json: {
          id: 'reading-2',
          kundli_id: 'profile-1',
          reading_type: request.postDataJSON()['period'],
          period_label: 'Generated now',
          content: 'New generated reading from the API.',
          generated_at: '2026-07-28T08:00:00Z',
          generated_local_date: '2026-07-28',
          version: 1,
        },
      });
      return;
    }

    const claimMatch = url.pathname.match(/^\/api\/v1\/readings\/profile-1\/claims\/([^/]+)$/);
    if (claimMatch && request.method() === 'PATCH') {
      const id = claimMatch[1];
      const body = request.postDataJSON();
      const index = state.claims.findIndex((claim) => claim['id'] === id);
      state.claims[index] = { ...state.claims[index], status: body['status'] };
      await route.fulfill({ json: state.claims[index] });
      return;
    }

    await route.fulfill({ status: 503, json: { detail: `Unmocked ${request.method()} ${url.pathname}` } });
  });

  return state;
}

test('mobile Notes and Readings avoid false persistence and load real claims', async ({ page }, testInfo) => {
  phoneOnly(testInfo.project.name);
  await page.setViewportSize({ width: 375, height: 812 });
  await mockMobileApi(page);

  await page.goto('/m/notes');
  await expect(page.getByText('Local draft', { exact: true })).toBeVisible();
  await expect(page.getByText(/not synced to your AstroSpace account/)).toBeVisible();
  await expect(page.getByText(/Stored privately on your account/)).toHaveCount(0);
  await expect(page.getByText(/^Saved$/)).toHaveCount(0);

  await page.getByRole('textbox', { name: 'Local draft notes' }).fill('Temporary local note');
  await page.reload();
  await expect(page.getByRole('textbox', { name: 'Local draft notes' })).toHaveValue('');

  await page.goto('/m/readings');
  await expect(page.getByText('Mercury week reading from the API.')).toBeVisible();
  await expect(page.getByText('1 of 2 held or partly held')).toBeVisible();
  await expect(page.getByText('3 total claims for Anika Rao')).toBeVisible();
  await expect(page.getByText('18 of 24 held up')).toHaveCount(0);
  await expect(page.getByText('WEEK OF 20-26 JULY')).toHaveCount(0);

  await page.getByRole('link', { name: /1 of 2 held or partly held/ }).click();
  await expect(page).toHaveURL(/\/m\/readings\/accuracy$/);
  await expect(page.getByText('3 claims returned')).toBeVisible();
  await expect(page.getByText('1 pending')).toBeVisible();
  await expect(page.getByText('1 accurate')).toBeVisible();
  await expect(page.getByText('1 missed')).toBeVisible();

  await page
    .locator('.mra-claim')
    .filter({ hasText: 'A delayed payment clears before the weekend.' })
    .getByRole('button', { name: 'partly' })
    .click();
  await expect(page.getByText('0 pending')).toBeVisible();
  await expect(page.getByText('1 partly')).toBeVisible();
});

test('mobile profile management adds, edits, deletes and switches safely', async ({ page }, testInfo) => {
  phoneOnly(testInfo.project.name);
  await page.setViewportSize({ width: 375, height: 812 });
  await mockMobileApi(page);

  await page.goto('/m/settings');
  await page.getByRole('link', { name: /Manage profiles/ }).click();
  await expect(page).toHaveURL(/\/m\/settings\/profiles$/);
  await expect(page.getByText('Anika Rao')).toBeVisible();
  await expect(page.getByText('Ravi Rao')).toBeVisible();

  await page.getByRole('link', { name: 'Add' }).click();
  await page.getByRole('textbox', { name: 'NAME' }).fill('Mira Rao');
  await page.getByRole('textbox', { name: 'RELATION' }).fill('child');
  await page.getByLabel('DATE OF BIRTH').fill('2018-05-11');
  await page.getByLabel('TIME OF BIRTH').fill('06:45');
  await page.getByRole('textbox', { name: 'PLACE OF BIRTH' }).fill('Pune');
  await page.getByRole('textbox', { name: 'COUNTRY CODE' }).fill('IN');
  await page.getByRole('button', { name: 'Add Profile' }).click();
  await expect(page).toHaveURL(/\/m\/settings\/profiles$/);
  await expect(page.getByText('Mira Rao')).toBeVisible();

  await page.goto('/m/settings/profiles/profile-3/edit');
  await page.getByRole('textbox', { name: 'NAME' }).fill('Mira Iyer');
  await page.getByRole('button', { name: 'Save Changes' }).click();
  await expect(page).toHaveURL(/\/m\/settings\/profiles$/);
  await expect(page.getByText('Mira Iyer')).toBeVisible();

  await page.goto('/m/settings/profiles/profile-3/delete');
  await expect(page.getByText('The active profile will switch to another available profile after deletion.')).toBeVisible();
  await page.getByRole('textbox', { name: 'TYPE DELETE TO CONFIRM' }).fill('DELETE');
  await page.getByRole('button', { name: 'Delete Profile' }).click();
  await expect(page).toHaveURL(/\/m\/settings\/profiles$/);
  await expect(page.getByText('Mira Iyer')).toHaveCount(0);
  await expect(page.locator('.profile-card.active').filter({ hasText: 'Anika Rao' })).toBeVisible();
});

test('mobile calendar uses calendar-intelligence data for month and day views', async ({ page }, testInfo) => {
  phoneOnly(testInfo.project.name);
  await page.setViewportSize({ width: 375, height: 812 });
  await mockMobileApi(page);

  await page.goto('/m/calendar');
  await expect(page.getByText('July 2026')).toBeVisible();
  await expect(page.getByText('API transit opening')).toBeVisible();
  await expect(page.getByText('Mercury supports follow-up calls.')).toBeVisible();
  await expect(page.getByText('Naga Panchami')).toHaveCount(0);

  await page.getByRole('button', { name: 'Next month' }).click();
  await expect(page.getByText('August 2026')).toBeVisible();
  await expect(page.getByText('August focus')).toBeVisible();

  await page.goto('/m/calendar/day?date=2026-07-29');
  await expect(page.getByRole('heading', { name: 'Wednesday, July 29' })).toBeVisible();
  await expect(page.getByText('Ekadashi · Rohini · Wednesday')).toBeVisible();
  await expect(page.getByText('Use extra care today')).toBeVisible();
  await expect(page.getByText('Abhijit Muhurta')).toBeVisible();
  await expect(page.getByText('API transit opening')).toBeVisible();
  await expect(page.getByText('Venus')).toBeVisible();
});

test('mobile compatibility selects saved people and computes endpoint-backed results', async ({ page }, testInfo) => {
  phoneOnly(testInfo.project.name);
  await page.setViewportSize({ width: 375, height: 812 });
  await mockMobileApi(page);

  await page.goto('/m/compat');
  await expect(page.getByText('Anika Rao x Ravi Rao')).toBeVisible();
  await expect(page.getByText('Lakshmi + Ravi')).toHaveCount(0);

  await page.getByRole('link', { name: /Anika Rao x Ravi Rao/ }).click();
  await expect(page).toHaveURL(/\/m\/compat\/results\?partner=profile-2$/);
  await expect(page.getByText('API workable match')).toBeVisible();
  await expect(page.getByText('28')).toBeVisible();
  await expect(page.getByText('Nadi matched from API')).toBeVisible();
  await expect(page.getByText('Backend compatibility note.')).toBeVisible();

  await page.goto('/m/compat/add');
  await page.getByRole('textbox', { name: 'NAME' }).fill('Nisha Kapoor');
  await page.getByLabel('DATE OF BIRTH').fill('1994-11-22');
  await page.getByLabel('TIME OF BIRTH').fill('10:15');
  await page.getByRole('textbox', { name: 'PLACE OF BIRTH' }).fill('Delhi');
  await page.getByRole('textbox', { name: 'COUNTRY CODE' }).fill('IN');
  await page.getByRole('button', { name: 'Check compatibility' }).click();
  await expect(page).toHaveURL(/\/m\/compat\/results\?partner=profile-3$/);
  await expect(page.getByText('Anika Rao x Nisha Kapoor')).toBeVisible();
  await expect(page.getByText('API high-support match')).toBeVisible();
  await expect(page.getByText('31')).toBeVisible();
  await expect(page.getByText('Nisha Kapoor adds steady emotional texture.')).toBeVisible();
});

test('mobile chart screens use endpoint-backed chart depth', async ({ page }, testInfo) => {
  phoneOnly(testInfo.project.name);
  await page.setViewportSize({ width: 375, height: 812 });
  await mockMobileApi(page);

  await page.goto('/m/chart');
  await expect(page.getByText('Aries Sun, Taurus Moon, Cancer rising.')).toBeVisible();
  await expect(page.getByText('Gemini Sun · Cancer Moon · Taurus rising')).toHaveCount(0);
  await page.getByRole('button', { name: /Computed transparently/ }).click();
  await expect(page.getByText('Mock Swiss Ephemeris')).toBeVisible();
  await page.locator('.panel').press('Escape');

  await page.goto('/m/chart/full');
  await page.getByRole('button', { name: /Su in Ar/ }).click();
  await expect(page.getByText('Sun in Aries')).toBeVisible();
  await expect(page.getByText(/computed from the selected profile rather than fixed example text/i)).toBeVisible();
  await page.locator('.panel').press('Escape');
  await page.getByRole('radio', { name: 'South' }).click();
  await page.getByRole('button', { name: 'Me' }).click();
  await expect(page.getByText('Mercury in Libra')).toBeVisible();
  await page.locator('.panel').press('Escape');

  await page.goto('/m/chart/vargas');
  await expect(page.getByText('D9 · Navamsha')).toBeVisible();
  await expect(page.getByText('Moon in Taurus is vargottama in this chart.')).toBeVisible();
  await page.getByRole('button', { name: 'D10' }).click();
  await expect(page.getByText('D10 · Dashamsha')).toBeVisible();
  await expect(page.getByText('Career and public work')).toBeVisible();

  await page.goto('/m/chart/periods');
  await expect(page.getByText('Moon → Saturn → Mercury')).toBeVisible();
  await expect(page.getByText(/As of 2026-07-28/)).toBeVisible();
  await page.getByRole('tab', { name: 'Yogini' }).click();
  await expect(page.getByRole('heading', { name: 'Dhanya' })).toBeVisible();

  await page.goto('/m/chart/yogas');
  await expect(page.getByText('API Chandra-Mangala Yoga')).toBeVisible();
  await expect(page.getByText('Moon and Mars relationship returned by API.')).toBeVisible();
  await expect(page.getByText('Gajakesari Yoga')).toHaveCount(0);

  await page.goto('/m/chart/strength');
  await expect(page.getByText('Sun')).toBeVisible();
  await expect(page.getByText('426 virupa · needs 360')).toBeVisible();
  await page.getByRole('button', { name: 'Ashtakavarga' }).click();
  await expect(page.getByText('327 total bindus')).toBeVisible();
  await page.getByRole('button', { name: 'Jaimini' }).click();
  await expect(page.getByText('Atmakaraka')).toBeVisible();
  await expect(page.getByText('Bhava Lagna')).toBeVisible();
});

test('mobile remedies and muhurta use available backend-backed inputs honestly', async ({ page }, testInfo) => {
  phoneOnly(testInfo.project.name);
  await page.setViewportSize({ width: 375, height: 812 });
  await mockMobileApi(page);

  await page.goto('/m/remedies');
  await expect(page.getByText('For your active Saturn period')).toBeVisible();
  await expect(page.getByText(/Saturn is active in the returned dasha stack/)).toBeVisible();
  await expect(page.getByText('Manglik check')).toBeVisible();
  await expect(page.getByText('Mars check returned by API.')).toBeVisible();
  await expect(page.getByText('For Saturn’s friction at work')).toHaveCount(0);

  await page.goto('/m/muhurta');
  await expect(page.getByText(/Using your current location/)).toHaveCount(0);
  await page.getByRole('radio', { name: 'This week' }).click();
  await page.getByRole('button', { name: 'Find windows' }).click();
  await expect(page).toHaveURL(/\/m\/muhurta\/results\?goal=contract&range=week$/);
  await expect(page.getByText('Wednesday, July 29')).toBeVisible();
  await expect(page.getByText('12:05 – 12:55')).toBeVisible();
  await expect(page.getByText(/Abhijit Muhurta returned by the panchanga calculation/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Calendar export not available yet' }).first()).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Reminders need native support' }).first()).toBeDisabled();
  await expect(page.getByText('Tuesday, 29 July')).toHaveCount(0);
});

test('mobile notification platform states are explicit and retryable', async ({ page }, testInfo) => {
  phoneOnly(testInfo.project.name);
  await page.setViewportSize({ width: 375, height: 812 });
  await mockMobileApi(page);

  await page.goto('/m/settings/notifications');
  await expect(page.getByText(/Notification choices persist on this device/)).toBeVisible();
  await page.getByRole('switch', { name: 'Morning brief' }).click();
  await page.reload();
  await expect(page.getByRole('switch', { name: 'Morning brief' })).toHaveAttribute('aria-checked', 'false');

  await page.goto('/m/notifications');
  await expect(page.getByText(/Notifications are unavailable/)).toBeVisible();
  await page.getByRole('button', { name: 'Retry' }).click();
  await expect(page.getByText('API transit alert')).toBeVisible();
  await page.getByRole('button', { name: /API transit alert/ }).click();
  await expect(page).toHaveURL(/\/m\/transits$/);
});

test('mobile persona modes change navigation and presentation depth', async ({ page }, testInfo) => {
  phoneOnly(testInfo.project.name);
  await page.setViewportSize({ width: 375, height: 812 });
  await mockMobileApi(page);

  await page.goto('/m/settings/mode');
  await page.getByRole('radio', { name: /Guided/ }).click();
  await page.goto('/m/ask');
  await expect(page.getByText('What to do')).toBeVisible();
  await expect(page.getByText('Chart', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Ask in plain language.')).toBeVisible();
  await expect(page.getByRole('button', { name: /Money/ })).toHaveCount(0);
  await expect(page.getByText('Plain-language starter')).toBeVisible();

  await page.goto('/m/settings/mode');
  await page.getByRole('radio', { name: /Practitioner/ }).click();
  await page.goto('/m/ask');
  await expect(page.getByText('Periods')).toBeVisible();
  await expect(page.getByText('Transits')).toBeVisible();
  await expect(page.getByText('Ask', { exact: true })).toHaveCount(1);
  await expect(page.getByText('Ask with chart context.')).toBeVisible();
  await expect(page.getByText('Technical depth')).toBeVisible();
  await expect(page.getByRole('button', { name: /Money/ })).toBeVisible();
});
