import { DailyGuidancePayload } from '../../../core/models';
import { ExperienceMode, ReadingTone } from '../../../core/preferences.service';

export interface AudioReadingSection {
  label: string;
  text: string;
}

interface AudioScriptInput {
  name: string;
  dateLabel: string;
  city: string;
  daily: DailyGuidancePayload;
  experienceMode: ExperienceMode;
  tone: ReadingTone;
}

export function buildTodayAudioScript({
  name,
  dateLabel,
  city,
  daily,
  experienceMode,
  tone,
}: AudioScriptInput): AudioReadingSection[] {
  const firstName = name.split(/\s+/)[0] || name;
  const gentle = tone === 'gentle';
  const difficult = daily.verdict.tone === 'caution' || daily.verdict.tone === 'mixed';
  const lead = difficult
    ? gentle
      ? 'There may be a few uneven moments, so we will keep this practical and kind.'
      : 'The day needs steadiness and cleaner choices.'
    : gentle
      ? 'There is enough steadiness here to move gently and still make progress.'
      : 'The day supports clear, useful action.';

  const sections: AudioReadingSection[] = [
    {
      label: 'Opening',
      text: [
        `Namaste, ${firstName}.`,
        `Here is your reading for ${dateLabel} in ${city}.`,
        lead,
      ].join(' '),
    },
    {
      label: 'Overview',
      text: [
        daily.verdict.headline,
        soften(daily.reading.summary, gentle),
        sentence(daily.reading.focus, 'Your focus is'),
      ].filter(Boolean).join(' '),
    },
    {
      label: 'Today',
      text: [
        `A good use of the day is: ${daily.do_today[0]?.text ?? daily.reading.best_for[0] ?? daily.reading.focus}.`,
        `Try to avoid: ${daily.avoid_today[0]?.text ?? daily.reading.avoid[0] ?? daily.reading.timing_note}.`,
        `For timing, ${lowerFirst(daily.reading.timing_note)}`,
      ].join(' '),
    },
    {
      label: 'Why',
      text: whySection(daily, experienceMode),
    },
    {
      label: 'Close',
      text: difficult
        ? 'Take the day one step at a time. Use the reading as a steadying mirror, not a pressure.'
        : 'Move with attention, and let the day stay simple. That is enough.',
    },
  ];

  return sections.filter((section) => section.text.trim().length > 0);
}

function whySection(daily: DailyGuidancePayload, experienceMode: ExperienceMode): string {
  const plain = daily.reading.plain_why.slice(0, experienceMode === 'guided' ? 1 : 2);
  if (experienceMode === 'practitioner') {
    const technical = daily.reading.technical_why.slice(0, 2);
    return [
      ...plain,
      `The panchang shows ${daily.star_of_day.tithi}, ${daily.star_of_day.nakshatra}, and Moon in ${daily.star_of_day.moon_rashi}.`,
      `Tarabala is ${daily.tarabala.favourable ? 'supportive' : 'sensitive'}; Chandrabala is ${daily.chandrabala.favourable ? 'supportive' : 'sensitive'}.`,
      ...technical,
    ].join(' ');
  }
  if (experienceMode === 'balanced') {
    return [
      ...plain,
      `The main daily signals are ${daily.tarabala.favourable ? 'supportive' : 'sensitive'} Tarabala and ${daily.chandrabala.favourable ? 'supportive' : 'sensitive'} Chandrabala.`,
    ].join(' ');
  }
  return plain.join(' ');
}

function soften(value: string, gentle: boolean): string {
  if (!gentle) return value;
  return value
    .replace(/\bmust\b/gi, 'may want to')
    .replace(/\bavoid\b/gi, 'be careful with')
    .replace(/\bbad\b/gi, 'sensitive');
}

function sentence(value: string | undefined, prefix: string): string {
  if (!value) return '';
  const normalized = value.trim();
  if (!normalized) return '';
  return `${prefix} ${lowerFirst(normalized)}`;
}

function lowerFirst(value: string): string {
  return value ? value.charAt(0).toLowerCase() + value.slice(1) : value;
}
