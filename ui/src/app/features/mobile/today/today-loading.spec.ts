import { NaturalVoiceService } from '../../../core/natural-voice.service';
import { SubhashitaService } from '../../../core/subhashita.service';
import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { TodayComponent } from './today.component';
import { KundliStore } from '../../../core/kundli.store';
import { VedicService } from '../../../core/vedic.service';
import { FestivalService } from '../../../core/festival.service';
import { AnalyticsService } from '../../../core/analytics.service';
import { PreferencesService } from '../../../core/preferences.service';
import { HapticsService } from '../../../core/haptics.service';
import { DailyBriefResponse, DailyGuidancePayload } from '../../../core/models';

/** A real engine payload (New Delhi chart, 2026-07-21). */
const DAILY_FIXTURE = {
  "system": "AstroSpace Daily Guidance",
  "engine_version": "daily-guidance-1.1",
  "valid_from": "2026-07-21T05:36:10+05:30",
  "valid_until": "2026-07-22T05:36:43+05:30",
  "day_definition": "sunrise_to_next_sunrise",
  "as_of": "2026-07-21T10:00:00+05:30",
  "date": "2026-07-21",
  "subject": "Daily",
  "relation": "self",
  "vara": "Tuesday",
  "verdict": {
    "tone": "caution",
    "score": -9,
    "headline": "A day to pull back and observe",
    "text": "Today looks like a day to pull back and observe for you. Your own birth star returns. Retreat, reflect, and refuse to rush. The Moon crosses a shadow zone. Expect emotional static—don't force a resolution. A long-term cosmic tailwind is at your back. Lean into the momentum. Practically, keep 15:53–17:35 for routine work rather than fresh starts. Overall, disappear into the background until the weather breaks.",
    "word_count": 66
  },
  "reading": {
    "summary": "The sky is heavy. It's a day for you to retreat and observe.",
    "focus": "Downshift. This is a day for maintenance, rest, and ignoring manufactured urgency.",
    "best_for": [
      "Growth: lean into whatever feels meaningful, not just urgent — Guru Bala from Lagna is active.",
      "Career: worth pushing the task that actually matters — your current Saturn period favours this."
    ],
    "avoid": [
      "Today's tara is Janma — your birth star returns, making this a reflective, inward day best kept for routine rather than fresh launches.",
      "Finance: not the day for financial risk-taking — Sade Sati is active.",
      "Health: go easy on yourself today — Rahu caution from Moon is active."
    ],
    "energy": "drained",
    "relationship_tone": "Tension is high. Do not go digging for emotional closure today.",
    "money_tone": "Keep your wallet closed. Everything looks like a better idea than it actually is.",
    "work_tone": "Lower your expectations. Plan, document, and survive the meeting.",
    "timing_note": "Avoid starting anything crucial during 15:53–17:35. Use that window to clean house instead.",
    "plain_why": [
      "Your personal timing marker points inward. It's a day for reflection, not action.",
      "The Moon sits in its most vulnerable house for you. Emotions will run hot.",
      "A slow-moving transit is actively supporting your chart, granting long-term clarity."
    ],
    "technical_why": [
      "Nakshatra: Chitra",
      "Tithi: Ashtami Shukla",
      "Tarabala: Janma (1/9)",
      "Chandrabala: house 8 from natal Moon",
      "Dasha: Saturn / Saturn / Jupiter / Saturn",
      "Transit rule: Sade Sati (high)",
      "Transit rule: Guru Bala from Lagna (supportive)",
      "Transit rule: Rahu caution from Moon (medium)",
      "Rahu Kalam: 15:53–17:35"
    ]
  },
  "color": {
    "name": "Coral Red",
    "hex": "#D0342C",
    "planet": "Mars",
    "source": "colour of Mars, lord of today's weekday (vara)",
    "power_color": {
      "name": "Golden Yellow",
      "hex": "#D8A128",
      "planet": "Jupiter",
      "source": "Jupiter is running a supportive transit for this profile"
    },
    "caution_color": {
      "name": "Deep Blue",
      "hex": "#365B9E",
      "planet": "Saturn",
      "source": "Saturn is running a challenging transit; ease off this shade today"
    }
  },
  "number": {
    "value": 2,
    "fit": "favourable",
    "ruling_planet": "Mars",
    "ruling_number": 9,
    "personal_good": [
      1,
      2,
      3,
      9
    ],
    "personal_evil": [
      6,
      8
    ],
    "source": "digital root of today's date; ruling number from the weekday lord (vara); fit judged against birth numerology"
  },
  "tarabala": {
    "tara": "Janma",
    "count": 1,
    "favourable": false,
    "note": "Janma tara — avoid major beginnings"
  },
  "chandrabala": {
    "house_from_rashi": 8,
    "favourable": false,
    "chandrashtama": true
  },
  "star_of_day": {
    "nakshatra": "Chitra",
    "moon_rashi": "Virgo",
    "tithi": "Ashtami Shukla"
  },
  "panchanga_details": {
    "tithi": "Ashtami Shukla",
    "nakshatra": "Chitra",
    "yoga": "Siddha",
    "karana": "Vishti",
    "vara": "Tuesday"
  },
  "masa": {
    "amanta": "Ashadha",
    "purnimanta": "Ashadha",
    "adhika": false,
    "paksha": "Shukla",
    "is_convention_dependent": true,
    "observance_note": "Amanta reckoning is used for names here; purnimanta readers (most of North India) will see the next month's name during Krishna paksha."
  },
  "muhurta_windows": [
    {
      "name": "Rahu Kalam",
      "time": "15:53–17:35",
      "kind": "inauspicious"
    },
    {
      "name": "Yamaganda",
      "time": "09:01–10:44",
      "kind": "inauspicious"
    },
    {
      "name": "Gulika Kalam",
      "time": "12:27–14:10",
      "kind": "inauspicious"
    },
    {
      "name": "Abhijit Muhurta",
      "time": "12:00–12:54",
      "kind": "auspicious"
    }
  ],
  "do_today": [
    {
      "headline": "Growth: lean into whatever feels meaningful, not just urgent",
      "text": "Growth: lean into whatever feels meaningful, not just urgent — Guru Bala from Lagna is active.",
      "source": "domain",
      "domain": "Growth"
    },
    {
      "headline": "Career: worth pushing the task that actually matters",
      "text": "Career: worth pushing the task that actually matters — your current Saturn period favours this.",
      "source": "domain",
      "domain": "Career"
    }
  ],
  "avoid_today": [
    {
      "headline": "Your tara today: Janma",
      "plain_headline": "A reflective, inward day",
      "text": "Today's tara is Janma — your birth star returns, making this a reflective, inward day best kept for routine rather than fresh launches.",
      "source": "tarabala"
    },
    {
      "headline": "Finance: not the day for financial risk-taking",
      "text": "Finance: not the day for financial risk-taking — Sade Sati is active.",
      "source": "domain",
      "domain": "Finance"
    },
    {
      "headline": "Health: go easy on yourself today",
      "text": "Health: go easy on yourself today — Rahu caution from Moon is active.",
      "source": "domain",
      "domain": "Health"
    }
  ],
  "lucky_signature": {
    "gem": "Yellow Sapphire",
    "metal": "Gold",
    "direction": "North-East",
    "days": [
      "Monday",
      "Tuesday",
      "Thursday"
    ]
  },
  "lucky_numbers": {
    "numerology": {
      "number": 1,
      "ruling_planet": "Sun",
      "good_numbers": [
        1,
        2,
        3,
        9
      ],
      "evil_numbers": [
        6,
        8
      ],
      "source": "digital root of birth day-of-month (moolank)"
    },
    "astrological": {
      "number": 3,
      "planet": "Jupiter",
      "source": "Lagna lord (ascendant ruler) — the chart's primary identity indicator",
      "witnesses": [
        {
          "label": "Lagna lord",
          "planet": "Jupiter",
          "number": 3
        },
        {
          "label": "Rashi (Moon) lord",
          "planet": "Saturn",
          "number": 8
        },
        {
          "label": "Nakshatra lord",
          "planet": "Mars",
          "number": 9
        },
        {
          "label": "Atmakaraka",
          "planet": "Saturn",
          "number": 8
        }
      ],
      "confirmed_by": [],
      "confirmation_count": 0
    }
  },
  "context": {
    "route_domain": "health",
    "dasha_chain": [
      {
        "level": "mahadasha",
        "lord": "Saturn"
      },
      {
        "level": "antardasha",
        "lord": "Saturn"
      },
      {
        "level": "pratyantardasha",
        "lord": "Jupiter"
      },
      {
        "level": "sookshmadasha",
        "lord": "Saturn"
      }
    ],
    "references": [
      {
        "ref_id": "uk_1st_lagna_vitality",
        "domains": [
          "health"
        ],
        "statement": "The Lagna (1st bhava) and its lord govern overall vitality and constitution; a strong, undamaged Lagna lord is classically read as a baseline of resilience that other houses' afflictions play out against.",
        "source_text_key": "uttara_kalamrita",
        "source_location": "Lagna significations",
        "subdomains": [
          "vitality"
        ],
        "tags": [
          "house:1"
        ],
        "status": "verified_common"
      },
      {
        "ref_id": "bphs17_1_sixth_scope",
        "domains": [
          "health"
        ],
        "statement": "The 6th bhava governs disease, and ulcers or bruises of the body.",
        "source_text_key": "bphs",
        "source_location": "ch.17 v.1, p.113 (Santhanam trans.)",
        "subdomains": [
          "acute_disease",
          "chronic_disease"
        ],
        "tags": [
          "house:6"
        ],
        "status": "verified_common"
      },
      {
        "ref_id": "bphs17_2_sixth_lord_and_limb",
        "domains": [
          "health"
        ],
        "statement": "The 6th lord in the 6th, the lagna or the 8th indicates ulcers or bruises on the body; the sign falling in the 6th indicates which limb is concerned.",
        "source_text_key": "bphs",
        "source_location": "ch.17 v.2, p.113 (Santhanam trans.)",
        "subdomains": [
          "acute_disease",
          "accidents_surgery"
        ],
        "tags": [
          "house:6",
          "lord:6"
        ],
        "status": "verified_common"
      }
    ],
    "active_gochara": [
      {
        "name": "Sade Sati",
        "planet": "Saturn",
        "severity": "high",
        "av_bindus": 3
      },
      {
        "name": "Guru Bala from Lagna",
        "planet": "Jupiter",
        "severity": "supportive",
        "av_bindus": 3
      },
      {
        "name": "Rahu caution from Moon",
        "planet": "Rahu",
        "severity": "medium",
        "av_bindus": null
      },
      {
        "name": "Ketu caution from Moon",
        "planet": "Ketu",
        "severity": "medium",
        "av_bindus": null
      },
      {
        "name": "Mars trigger from Moon",
        "planet": "Mars",
        "severity": "medium",
        "av_bindus": 5
      }
    ]
  },
  "provenance": {
    "engine": "computed from panchanga + gochara via the Context Engine",
    "place": {
      "city": "New Delhi",
      "nation": "IN",
      "timezone": "Asia/Kolkata"
    },
    "note": "Every line is rule-derived; expand any card to see its source signal."
  }
} as unknown as DailyGuidancePayload;

/**
 * Today flickered on the phone as if it were refreshing itself (2026-10-16).
 * Its load effect called loadToday() inside the effect, so every signal that
 * loadToday read synchronously became a dependency, including loadedDaily,
 * which it then wrote. Each run re-armed itself: the cards were rebuilt,
 * the saved guidance re-read and the brief re-fetched in a loop.
 */
describe('TodayComponent loading', () => {
  const profile = { id: 'p1', name: 'Hawk', birth_city: 'New Delhi', birth_nation: 'IN' };
  const other = { id: 'p2', name: 'Asha', birth_city: 'New Delhi', birth_nation: 'IN' };
  let vedic: jasmine.SpyObj<VedicService>;

  const brief: DailyBriefResponse = {
    date: DAILY_FIXTURE.date,
    valid_until: null,
    source: 'agent',
    brief: {
      card_title: 'Finish what you started',
      headline: 'A steady day',
      summary: 'Keep to the plan.',
      narrative: 'Keep to the plan.',
      practical_close: 'Begin before Rahu Kalam.',
      focus: 'Finishing',
      energy: 'steady',
      areas: { love: 'calm', money: 'even', work: 'busy', health: 'rest', growth: 'slow' },
      do: [{ headline: 'Finish one task', detail: 'Tarabala supports it.' } as never],
      avoid: [{ headline: 'Rush a reply', detail: 'Chandrabala is weak.' } as never],
      timing_note: 'Rahu Kalam as given.',
      why: ['Tarabala is good.'],
      spoken: [{ label: 'Opening', text: 'Namaste Hawk.' }],
    },
  };

  beforeEach(() => {
    vedic = jasmine.createSpyObj<VedicService>('VedicService', [
      'cachedDailyGuidanceEntry', 'refreshDailyGuidance', 'dailyGuidance', 'dailyBrief', 'calendarIntelligence', 'all', 'cachedAll',
    ]);
    vedic.cachedAll.and.returnValue(null);
    vedic.cachedDailyGuidanceEntry.and.returnValue({ data: DAILY_FIXTURE, freshness: 'fresh', storedAt: Date.now() } as never);
    vedic.dailyBrief.and.resolveTo(brief);
    vedic.calendarIntelligence.and.rejectWith(new Error('offline'));
    vedic.all.and.rejectWith(new Error('offline'));

    TestBed.configureTestingModule({
      providers: [
        { provide: VedicService, useValue: vedic },
        {
          provide: KundliStore,
          useValue: {
            loaded: signal(true),
            activeId: signal('p1'),
            kundlis: signal([profile, other]),
            active: signal(profile),
            owner: signal(profile),
            load: () => Promise.resolve(),
          },
        },
        {
          provide: PreferencesService,
          useValue: {
            panchangaContextKey: signal('k'),
            tone: signal('balanced'),
            experienceMode: signal('balanced'),
            ayanamsha: signal('Lahiri'),
            panchangaPlace: signal(null),
            festivalRegions: signal([]),
          },
        },
        { provide: FestivalService, useValue: {} },
        { provide: AnalyticsService, useValue: { track: () => undefined } },
        { provide: HapticsService, useValue: { tap: () => undefined } },
        { provide: NaturalVoiceService, useValue: { available: () => Promise.resolve(false) } },
        { provide: SubhashitaService, useValue: { today: () => null } },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: new Map() }, queryParamMap: of(convertToParamMap({})) } },
      ],
    });
  });

  async function settle(): Promise<void> {
    for (let i = 0; i < 10; i++) {
      TestBed.tick();
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve));
    }
  }

  it('builds the cards once and fetches the brief once for one day', async () => {
    const today = TestBed.runInInjectionContext(() => new TodayComponent());
    await settle();

    expect(vedic.cachedDailyGuidanceEntry).toHaveBeenCalledTimes(1);
    expect(vedic.dailyBrief).toHaveBeenCalledTimes(1);
    // The agent's words are on the card, not reverted to the template.
    const view = (today as unknown as { view: () => { verdict: string; cardTitle?: string } }).view();
    expect(view.verdict).toBe('A steady day');
    expect(view.cardTitle).toBe('Finish what you started');
  });

  it('still reloads when the profile changes', async () => {
    TestBed.runInInjectionContext(() => new TodayComponent());
    await settle();
    const store = TestBed.inject(KundliStore) as unknown as { activeId: ReturnType<typeof signal<string>> };
    store.activeId.set('p2');
    await settle();
    expect(vedic.cachedDailyGuidanceEntry.calls.allArgs()).toEqual([['p1'], ['p2']]);
  });

  it('never keeps the last profile\'s birth chart up under the new name', async () => {
    const p1Chart = { subject: 'p1 chart' } as never;
    const p2Chart = { subject: 'p2 chart' } as never;
    vedic.cachedAll.and.callFake((id: string) => (id === 'p1' ? p1Chart : null));
    const today = TestBed.runInInjectionContext(() => new TodayComponent());
    await settle();
    const natal = (today as unknown as { natal: () => unknown }).natal;
    expect(natal()).toBe(p1Chart);
    let resolveP2!: (value: never) => void;
    vedic.all.and.returnValue(new Promise((resolve) => (resolveP2 = resolve)));
    const store = TestBed.inject(KundliStore) as unknown as { activeId: ReturnType<typeof signal<string>> };
    store.activeId.set('p2');
    await settle();
    // Cleared at the switch, not when the new chart happens to land.
    expect(natal()).toBeNull();
    resolveP2(p2Chart);
    await settle();
    expect(natal()).toBe(p2Chart);
  });

  it('asks for the day, chart and calendar together when nothing is cached', async () => {
    vedic.cachedDailyGuidanceEntry.and.returnValue(null);
    vedic.dailyGuidance.and.returnValue(new Promise(() => undefined));
    TestBed.runInInjectionContext(() => new TodayComponent());
    await settle();
    expect(vedic.dailyGuidance).toHaveBeenCalledWith('p1');
    expect(vedic.all).toHaveBeenCalledWith('p1');
    expect(vedic.calendarIntelligence).toHaveBeenCalled();
  });
});
