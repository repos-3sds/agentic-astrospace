import { DailyGuidancePayload } from '../../../core/models';
import type { AskSuggestion } from './ask-home.component';

type Mode = 'guided' | 'balanced' | 'practitioner';

/** Plain-words gloss of a dasha level name, for the `because` line. */
const LEVEL_WORD: Record<string, string> = {
  mahadasha: 'major period', antardasha: 'sub-period', pratyantardasha: 'sub-sub-period', sookshmadasha: 'short period',
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
  const current = chain.at(-1);
  const transit = daily.context?.active_gochara?.[0];
  const nakshatra = daily.star_of_day?.nakshatra;
  const tone = daily.verdict?.tone;
  const dashaBecause = current
    ? `${current.lord} ${LEVEL_WORD[current.level] ?? current.level}${major && major.lord !== current.lord ? ` within ${major.lord}` : ''} is running`
    : undefined;
  const dayBecause = nakshatra ? `Moon in ${nakshatra} today${tone ? ` · ${tone === 'caution' ? 'a caution day' : 'a supportive day'}` : ''}` : undefined;
  const transitBecause = transit ? `${transit.planet} transit: ${transit.name}` : dashaBecause;

  if (mode === 'guided') {
    return [
      { prompt: current ? `What should I focus on at work during my ${current.lord} period?` : 'What should I focus on at work this week?', because: dashaBecause ?? 'Plain-language starter' },
      { prompt: nakshatra ? `Is today a good day to have a family conversation?` : 'How should I think about a family conversation?', because: dayBecause ?? 'Practical guidance' },
      { prompt: 'What is one thing to avoid today?', because: dayBecause ?? 'Safety-first daily prompt' },
    ];
  }
  if (mode === 'practitioner') {
    return [
      { prompt: current ? `How does the ${current.lord} ${LEVEL_WORD[current.level] ?? current.level} shape my career factors right now?` : 'Explain my current dasha with natal and transit factors', because: dashaBecause ?? 'Technical depth' },
      { prompt: transit ? `What does ${transit.planet}'s current transit mean for relationships in my chart?` : 'Which transit rules are driving today’s reading?', because: transitBecause ?? 'Provenance check' },
      { prompt: nakshatra ? `Is the Moon in ${nakshatra} a good time to start something new?` : 'Compare D1 and D9 factors for this relationship question', because: dayBecause ?? 'Chart-layer prompt' },
    ];
  }
  return [
    { prompt: current ? `What does my ${current.lord} period mean for work right now?` : 'What should I consider about my career right now?', because: dashaBecause ?? 'From your chart' },
    { prompt: transit ? `How is ${transit.planet}'s transit affecting my relationships?` : 'What does my chart say about relationships?', because: transitBecause ?? 'From your chart' },
    { prompt: nakshatra ? `Is today a good day to start something new?` : 'Is this a good week to start something new?', because: dayBecause ?? 'From today’s panchanga' },
  ];
}

function neutral(mode: Mode): AskSuggestion[] {
  if (mode === 'guided') {
    return [
      { prompt: 'What should I focus on at work this week?', because: 'Plain-language starter' },
      { prompt: 'What is one thing to avoid today?', because: 'Safety-first daily prompt' },
      { prompt: 'How should I think about a family conversation?', because: 'Practical guidance' },
    ];
  }
  if (mode === 'practitioner') {
    return [
      { prompt: 'Explain my current dasha with natal and transit factors', because: 'Technical depth' },
      { prompt: 'Which transit rules are driving today’s reading?', because: 'Provenance check' },
      { prompt: 'Compare D1 and D9 factors for this relationship question', because: 'Chart-layer prompt' },
    ];
  }
  return [
    { prompt: 'What should I consider about my career right now?' },
    { prompt: 'What does my chart say about relationships?' },
    { prompt: 'Is this a good week to start something new?' },
  ];
}
