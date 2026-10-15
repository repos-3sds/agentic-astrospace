import { DailyGuidancePayload } from '../../../core/models';
import { buildAskSuggestions } from './ask-suggestions';

function daily(): DailyGuidancePayload {
  return {
    verdict: { tone: 'caution' },
    star_of_day: { nakshatra: 'Hasta', moon_rashi: 'Virgo', tithi: 'Panchami' },
    context: {
      dasha_chain: [{ level: 'mahadasha', lord: 'Saturn' }, { level: 'antardasha', lord: 'Mercury' }],
      active_gochara: [{ name: 'Jupiter over natal Moon', planet: 'Jupiter', av_bindus: 5 }],
    },
  } as unknown as DailyGuidancePayload;
}

describe('buildAskSuggestions', () => {
  it('grounds each Balanced suggestion in this profile’s dasha, transit and day', () => {
    const rows = buildAskSuggestions(daily(), 'balanced');
    expect(rows.length).toBe(3);
    expect(rows[0].prompt).toContain('Mercury period');
    expect(rows[0].because).toBe('Mercury sub-period within Saturn is running');
    expect(rows[1].prompt).toContain('Jupiter');
    expect(rows[2].because).toContain('Moon in Hasta today');
    expect(rows[2].because).toContain('caution day');
  });

  it('never offers the old fixed strings or a financial-verdict prompt', () => {
    for (const mode of ['guided', 'balanced', 'practitioner'] as const) {
      for (const payload of [daily(), null]) {
        const text = buildAskSuggestions(payload, mode).map((row) => row.prompt).join(' | ');
        expect(text).not.toContain('big purchase');
        expect(text).not.toContain('Your Saturn period is active');
        expect(text).not.toContain('Moon is in Hasta today');
      }
    }
  });

  it('falls back to neutral prompts without a payload', () => {
    const rows = buildAskSuggestions(null, 'balanced');
    expect(rows.map((row) => row.prompt)).toEqual([
      'What should I consider about my career right now?',
      'What does my chart say about relationships?',
      'Is this a good week to start something new?',
    ]);
  });
});
