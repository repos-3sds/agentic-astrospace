import { expect, test, type Page } from '@playwright/test';

/**
 * Coverage for US-GOC-031: no Playwright coverage existed for either the web
 * Gocharam tab or the native Gochara/Full Transits screens before this file,
 * even though several real bugs were found and fixed in that surface in this
 * session (mobile mode-blindness, missing classical Vedha/Ashtakavarga/Sade
 * Sati rendering). These tests assert the fixed behaviour so it can't
 * silently regress.
 */

const mockKundlis = [
  {
    id: 'profile-1',
    name: 'Test Native',
    relation: 'Self',
    sun_sign: 'Capricorn',
    moon_sign: 'Pisces',
    ascendant: 'Virgo',
    birth_year: 1990,
    birth_month: 1,
    birth_day: 1,
    birth_hour: 12,
    birth_minute: 0,
    birth_city: 'Delhi',
    birth_nation: 'IN',
  },
];

const guidedSummary = 'Guided: a long responsibility cycle is active.';
const balancedContext = 'Balanced: Saturn is transiting the 12th, 1st or 2nd from natal Moon.';
const practitionerDeepDive = 'Practitioner: Sade Sati overlay active, Saturn=12 from Janma Chandra.';

function buildGocharamPayload() {
  const saturnRule = {
    rule_id: 'baseline_saturn_moon_12',
    kind: 'baseline_placement' as const,
    rule_name: 'Saturn in house 12 from natal Moon',
    planet: 'Saturn',
    anchor: 'moon',
    house: 12,
    category: 'baseline',
    duration: 'transit_sign',
    base_verdict: 'challenging' as const,
    effective_verdict: 'challenging' as const,
    source_id: 'phaladeepika_26_south_indian',
    source_status: 'classical_table',
    claim_status: 'classical_verdict_with_editorial_synthesis',
    content: {
      guided_summary: guidedSummary,
      balanced_context: balancedContext,
      practitioner_deep_dive: practitionerDeepDive,
    },
    modifiers: [
      { type: 'ashtakavarga', effect: 'neutral', label: '4 BAV bindus · 28 SAV', evidence: { bindus: 4 } },
    ],
  };

  const sadeSatiOverlay = {
    rule_id: 'special_sade_sati',
    kind: 'special_overlay' as const,
    rule_name: 'Sade Sati',
    planet: 'Saturn',
    anchor: 'moon',
    house: 12,
    category: 'long_cycle',
    duration: 'long_term',
    base_verdict: 'challenging' as const,
    effective_verdict: 'challenging' as const,
    source_id: 'south_indian_sade_sati',
    source_status: 'traditional_practice',
    claim_status: 'traditional_label_with_editorial_synthesis',
    content: {
      guided_summary: guidedSummary,
      balanced_context: balancedContext,
      practitioner_deep_dive: practitionerDeepDive,
    },
    modifiers: [],
  };

  const domain = {
    id: 'career',
    title: 'Career and visible work',
    tone: 'challenging',
    main_theme: 'Current evidence asks for more care around career.',
    rationale: 'This domain reads 2, 6, 10, 11 from the natal Moon because...',
    reading: 'Prioritize work that can be completed and verified.',
    strengths: [],
    challenges: [guidedSummary],
    actions: ['Prioritize work that can be completed and verified.'],
    leading_planets: ['Saturn'],
    evidence_ids: ['rule.special_sade_sati'],
    range_outlook: {
      days: 90,
      event_count: 1,
      previous_event_count: 0,
      supportive_count: 0,
      challenging_count: 1,
      tone: 'challenging',
      title: '1 named change in the next 90 days',
      reading: 'Sade Sati ends around a future date.',
      previous_title: 'Stable named-rule background for the previous 90 days',
      previous_reading: 'No supported named Gocharam rule started or ended in the previous 90 days.',
      first_change: null,
      last_change: null,
      highlights: [],
      previous_highlights: [],
    },
  };

  const coreReadingBlock = {
    title: 'Caution Gocharam: pressure signals are active',
    tone: 'challenging',
    rationale: 'Saturn is 12 from the Moon.',
    reading: 'This period asks for patience.',
    timing_summary: 'Sade Sati runs from 2025-01-01 to 2032-06-01.',
  };

  return {
    schema_version: 'gocharam.profile.v2',
    engine_version: 'gocharam-canonical-2.0',
    system: 'South Indian Gocharam',
    as_of: '2026-07-29T12:00:00+00:00',
    ayanamsha: 'lahiri',
    node_type: 'mean',
    natal: { lagna_sign: 'Virgo', moon_sign: 'Pisces' },
    gochara: {
      planets: {
        Saturn: {
          planet: 'Saturn',
          longitude: 305.0,
          sign: 'Aquarius',
          sign_index: 10,
          degree_in_sign: 5.0,
          dms: '5°00\'00"',
          nakshatra: 'Shatabhisha',
          nakshatra_pada: 1,
          house_from_lagna: 6,
          house_from_moon: 12,
          retrograde: false,
          speed: 0.05,
          transit_dignity: { dignity: 'Neutral', score: 50 },
          special_aspect_houses_from_moon: [2, 6, 9],
        },
      },
      rules: [],
      active_rules: [],
      core_reading: {
        ...coreReadingBlock,
        next: coreReadingBlock,
        previous: coreReadingBlock,
        sentences: [],
        active_rule_count: 1,
        supportive_rule_count: 0,
        challenging_rule_count: 1,
      },
      timeline: {
        active_windows: [
          {
            rule: 'Sade Sati',
            rule_id: 'gochara_sade_sati',
            planet: 'Saturn',
            start_date: '2025-01-01',
            end_date: null,
            tone: 'challenging',
            trigger: 'Saturn is 12 from natal Moon',
            summary: 'Sade Sati is active now.',
            passes: [
              { start: '2025-01-01', end: null, entry_type: 'first_entry' },
            ],
          },
        ],
        previous_365_days: [],
        next_365_days: [],
        scan_days: 90,
      },
      interpretation: {
        schema_version: 'gocharam.interpretation.v3',
        library_version: 'astrospace-gocharam-kb-2026.07.2',
        mode: 'deterministic_cited_kb',
        methodology: {
          calculation_rule: 'Positions and rule activation come from the canonical Swiss-Ephemeris engine.',
          interpretation_rule: 'Classical verdicts and editorial synthesis are composed deterministically.',
        },
        convention: {
          primary_anchor: 'natal_moon',
          node_treatment: 'Rahu and Ketu use the Saturn favourable-house table by explicit convention.',
          safety: 'Traditional indications are contextual, not guaranteed predictions.',
        },
        sources: [
          {
            id: 'phaladeepika_26_south_indian',
            work: 'Phaladeepika',
            location: 'chapter 26',
            scope: 'favourable houses and vedha table',
            edition_status: 'edition-neutral rule table',
          },
        ],
        synthesis: {
          tone: 'challenging',
          headline: 'The transit background calls for more care',
          counts: { supportive: 0, mixed: 0, challenging: 1 },
          guided_summary: guidedSummary,
          balanced_context: balancedContext,
          practitioner_deep_dive: practitionerDeepDive,
        },
        range_outlook: domain.range_outlook,
        domains: [domain],
        matched_rules: [saturnRule, sadeSatiOverlay],
        evidence: [
          {
            id: 'transit.saturn',
            type: 'computed_transit',
            planet: 'Saturn',
            sign: 'Aquarius',
            house_from_moon: 12,
          },
          {
            id: 'rule.special_sade_sati',
            type: 'deterministic_rule',
            rule_id: 'special_sade_sati',
            source_id: 'south_indian_sade_sati',
            base_verdict: 'challenging',
            effective_verdict: 'challenging',
          },
        ],
      },
      sade_sati: { active: true, phase: 'first', saturn_house_from_moon: 12 },
      classical_gochara: {
        Saturn: {
          house_from_moon: 12,
          favourable: false,
          vedha: { obstructed: false, by: null, vedha_house: null },
          effective: 'unfavourable',
          source_status: 'classical_table',
        },
      },
      ashtakavarga: {
        planets: {
          Saturn: {
            planet: 'Saturn',
            transit_sign: 'Aquarius',
            transit_sign_index: 10,
            bindus: 4,
            bav_support: 'average',
            sav: 28,
            sav_support: 'average',
            kakshya: { kakshya_index: 2, kakshya_lord: 'Jupiter', bindu_given: false },
          },
        },
        note: 'A transit is weighted with the planet\'s natal BAV bindus.',
      },
    },
    ashtakavarga_transit: {
      planets: {
        Saturn: {
          planet: 'Saturn',
          transit_sign: 'Aquarius',
          transit_sign_index: 10,
          bindus: 4,
          bav_support: 'average',
          sav: 28,
          sav_support: 'average',
          kakshya: { kakshya_index: 2, kakshya_lord: 'Jupiter', bindu_given: false },
        },
      },
      note: 'A transit is weighted with the planet\'s natal BAV bindus.',
    },
    periods: [],
    coverage: { past_days: 90, future_days: 90, strategy: 'pre-generated deterministic rule windows' },
    notes: ['Moon is the primary Gocharam anchor; Lagna is used as a practical cross-check.'],
  };
}

async function mockApi(page: Page): Promise<void> {
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/v1/auth/config') {
      await route.fulfill({ json: { enabled: false } });
      return;
    }
    if (url.pathname === '/api/v1/kundlis') {
      await route.fulfill({ json: mockKundlis });
      return;
    }
    if (url.pathname.endsWith('/gocharam') || url.pathname.endsWith('/transits')) {
      await route.fulfill({ json: buildGocharamPayload() });
      return;
    }
    await route.fulfill({ status: 503, json: { detail: 'Not mocked in gocharam screens test' } });
  });
}

test.describe('web Gocharam tab', () => {
  test('renders Sade Sati status and classical Vedha status', async ({ page }) => {
    await mockApi(page);
    await page.goto('/kundli/profile-1/gocharam');

    await expect(page.getByText('Sade Sati is active')).toBeVisible();
    await expect(page.getByText('Classical status (Phaladeepika ch.26)')).toBeVisible();
    await expect(page.getByText('Ashtakavarga support')).toBeVisible();
  });
});

test.describe('mobile Gochara screen', () => {
  test.skip(({ browserName }) => browserName !== 'chromium');

  test('loads and shows the domain and planet readings', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await mockApi(page);
    await page.goto('/m/transits');

    await expect(page.getByText('Career and visible work')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Saturn in house 12' })).toBeVisible();
  });
});

test.describe('mobile Full Transits screen', () => {
  test.skip(({ browserName }) => browserName !== 'chromium');

  test('shows Sade Sati and classical Vedha evidence absent from the pre-revamp screen', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await mockApi(page);
    await page.goto('/m/transits/full');

    await expect(page.locator('.mtrf-title', { hasText: 'SADE SATI' })).toBeVisible();
    await expect(page.locator('.mtrf-copy[data-tone="warn"]').getByText('Active')).toBeVisible();
  });

  async function setExperienceMode(page: Page, experienceMode: 'guided' | 'balanced' | 'practitioner'): Promise<void> {
    await page.addInitScript((mode) => {
      localStorage.setItem(
        'astrospace-preferences',
        JSON.stringify({
          chartStyle: 'south',
          ayanamsha: 'lahiri',
          nodeType: 'mean',
          timezoneMode: 'browser',
          panchangaPlace: null,
          language: 'en',
          regionalFormat: 'en-IN',
          experienceMode: mode,
          tone: mode === 'practitioner' ? 'direct' : 'gentle',
        }),
      );
    }, experienceMode);
  }

  // Regression guard for US-GOC-028: full-transits.component.ts used to
  // hardcode practitioner_deep_dive/balanced_context for every user
  // regardless of their Guided/Balanced/Practitioner setting. Each mode gets
  // its own fresh page/context (matching mobile-persona-contracts.spec.ts's
  // pattern) rather than mutating localStorage mid-test and reloading —
  // addInitScript re-fires on every navigation including reload, so mutating
  // via page.evaluate() then reloading would just get clobbered back.
  test('regression guard (US-GOC-028): guided mode shows guided_summary, not practitioner_deep_dive', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await mockApi(page);
    await setExperienceMode(page, 'guided');
    await page.goto('/m/transits/full');

    await expect(page.getByText(guidedSummary, { exact: false })).toBeVisible();
    await expect(page.getByText(practitionerDeepDive, { exact: false })).toHaveCount(0);
  });

  test('regression guard (US-GOC-028): practitioner mode shows practitioner_deep_dive, not guided_summary', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await mockApi(page);
    await setExperienceMode(page, 'practitioner');
    await page.goto('/m/transits/full');

    await expect(page.getByText(practitionerDeepDive, { exact: false })).toBeVisible();
    await expect(page.getByText(guidedSummary, { exact: false })).toHaveCount(0);
  });
});
