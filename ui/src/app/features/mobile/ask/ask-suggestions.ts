import { DailyGuidancePayload } from '../../../core/models';
import type { AskSuggestion } from './ask-home.component';

type Mode = 'guided' | 'balanced' | 'practitioner';

/** Plain-words gloss of a dasha level name, for the `because` line. */
const LEVEL_WORD: Record<string, string> = {
  mahadasha: 'major period', antardasha: 'sub-period', pratyantardasha: 'sub-sub-period', sookshmadasha: 'short period',
};

/** The same tone words Today uses; 'mixed' was read as supportive (U23). */
const TONE_WORD: Record<string, string> = {
  supportive: 'a supportive day', positive: 'a supportive day', mixed: 'a mixed day', caution: 'a caution day',
};

/**
 * Three suggestions, one per life area (work, relationships, timing), each
 * grounded in something the daily payload actually says about this
 * profile today. Nothing here asserts a verdict: a suggestion is a question
 * the reader may ask, with the chart fact it rests on shown beneath it.
 */
export function buildAskSuggestions(daily: DailyGuidancePayload | null, mode: Mode): AskSuggestion[] {
  if (!daily) return neutral(mode);
  const chain = daily.context?.dasha_chain ?? [];
  const major = chain[0];
  // The sub-period, not the deepest level: the chain runs to the 4th or 5th
  // level, which lasts days, and "Mars short period within Moon" read as the
  // main sub-period beside a Moon › Sun stack (regression 2026-10-17, M2).
  const current = chain[1] ?? major;
  const transit = daily.context?.active_gochara?.[0];
  const nakshatra = daily.star_of_day?.nakshatra;
  const tone = daily.verdict?.tone;
  const dashaBecause = !current
    ? undefined
    : mode === 'practitioner'
      ? `Running: ${chain.map((level) => level.lord).join(' › ')}`
      : current === major
        ? `${major.lord} major period is running`
        : `${current.lord} sub-period within the ${major.lord} major period`;
  const dayBecause = nakshatra ? `Moon in ${nakshatra} today${tone ? ` · ${TONE_WORD[tone] ?? 'a mixed day'}` : ''}` : undefined;
  const transitBecause = transit ? `${transit.planet} transit: ${transit.name}` : dashaBecause;

  if (mode === 'guided') {
    return [
      { prompt: current ? `What should I focus on at work during my ${current.lord} period?` : 'What should I focus on at work this week?', because: dashaBecause ?? 'A good place to start' },
      { prompt: nakshatra ? 'Is today a good day for a talk with my family?' : 'How should I approach a talk with my family?', because: dayBecause ?? 'For an everyday decision' },
      { prompt: 'What is one thing to avoid at work today?', because: dayBecause ?? 'To keep the day on track' },
    ];
  }
  if (mode === 'practitioner') {
    return [
      { prompt: current ? `How does the ${current.lord} ${LEVEL_WORD[current.level] ?? current.level} shape my career factors right now?` : 'Explain my current dasha for my career with natal and transit factors', because: dashaBecause ?? 'Dasha with natal and transit evidence' },
      { prompt: transit ? `What does ${transit.planet}'s current transit mean for relationships in my chart?` : 'Which transits are shaping my career today?', because: transitBecause ?? 'Today’s transits against your chart' },
      { prompt: nakshatra ? `Is the Moon in ${nakshatra} a good time to start a new business?` : 'Compare D1 and D9 factors for this relationship question', because: dayBecause ?? 'D1 read against D9' },
    ];
  }
  return [
    { prompt: current ? `What does my ${current.lord} period mean for work right now?` : 'What should I consider about my career right now?', because: dashaBecause ?? 'From your chart' },
    { prompt: transit ? `How is ${transit.planet}'s transit affecting my relationships?` : 'What does my chart say about relationships?', because: transitBecause ?? 'From your chart' },
    { prompt: nakshatra ? 'Is today a good day to start something new at work?' : 'Is this a good week to start something new at work?', because: dayBecause ?? 'From today’s panchanga' },
  ];
}

function neutral(mode: Mode): AskSuggestion[] {
  if (mode === 'guided') {
    return [
      { prompt: 'What should I focus on at work this week?', because: 'A good place to start' },
      { prompt: 'What is one thing to avoid at work today?', because: 'To keep the day on track' },
      { prompt: 'How should I approach a talk with my family?', because: 'For an everyday decision' },
    ];
  }
  if (mode === 'practitioner') {
    return [
      { prompt: 'Explain my current dasha for my career with natal and transit factors', because: 'Dasha with natal and transit evidence' },
      { prompt: 'Which transits are shaping my career today?', because: 'Today’s transits against your chart' },
      { prompt: 'Compare D1 and D9 factors for this relationship question', because: 'D1 read against D9' },
    ];
  }
  return [
    { prompt: 'What should I consider about my career right now?' },
    { prompt: 'What does my chart say about relationships?' },
    { prompt: 'Is this a good week to start something new at work?' },
  ];
}

/**
 * What a topic chip shows until this profile's own list arrives (or on the
 * web app, which has no chart-built list). Neutral on purpose: nothing here
 * claims a fact about the chart, and nothing assumes the reader is married or
 * has children. Each names its topic so the answer never has to ask which
 * area was meant. The chart-built lists come from
 * astrospace/core/vedic/ask_suggestions.py; a topic added there needs a row
 * here and a chip in AskHomeComponent.
 */
export const TOPIC_FALLBACK: Record<string, AskSuggestion[]> = {
  work: [
    { prompt: 'What does my current period mean for my work?' },
    { prompt: 'Which months in the coming year look better for my work?' },
    { prompt: 'What kind of work suits my chart best?' },
  ],
  marriage: [
    { prompt: 'What does my current period mean for marriage and partnership?' },
    { prompt: 'Which months in the coming year look better for marriage and partnership?' },
    { prompt: 'What does my chart say about my partner’s nature?' },
  ],
  money: [
    { prompt: 'What does my current period mean for money and savings?' },
    { prompt: 'Which months in the coming year look better for money and savings?' },
    { prompt: 'Where does money come to me most easily, by my chart?' },
  ],
  child: [
    { prompt: 'What does my current period mean for children?' },
    { prompt: 'Which months in the coming year look better for children?' },
    { prompt: 'What does my chart say about children?' },
  ],
  health: [
    { prompt: 'What does my current period mean for my health and energy?' },
    { prompt: 'Which months in the coming year look better for my health and energy?' },
    { prompt: 'What simple daily routine suits my health right now?' },
  ],
};
