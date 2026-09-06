import { askReportPdf, askReportText, AskReportInput } from './ask-report';

const INPUT: AskReportInput = {
  question: 'When does my career become more stable?',
  domain: 'career',
  intent: 'timing',
  createdAt: '2026-09-06T08:30:00Z',
  contextUsed: ['houses', 'vargas', 'dasha_relevance'],
  evidenceRefs: ['career_house_10', 'dasha_relevance'],
  profileContextRevision: 4,
  profileContextAsOf: '2026-09-05',
  fallbackContent: '',
  reading: {
    acknowledgment: 'You are asking about stability, not only a job change.',
    technical_basis: [
      {
        factor: '10th lord Mercury',
        reading: 'Mercury is supported in the career chart.',
        source: { ref_id: 'career_house_10', location: 'Chapter 10' },
      },
    ],
    interpretation: 'The period supports gradual consolidation.\n\nAvoid treating one transit as a guarantee.',
    summary_and_assurance: 'This is a constructive window with practical caveats.',
    guidance: {
      practical_actions: ['Keep written evidence of progress.', 'Review the timing after June.'],
      remedies: [{ practice: 'Thursday study or service', note: 'Optional traditional support, not a guarantee.' }],
      follow_up_questions: ['Which month is strongest?'],
    },
    confidence: 'medium',
  },
};

describe('Ask report export', () => {
  it('serializes every structured section and provenance instead of copying the summary only', () => {
    const text = askReportText(INPUT);
    expect(text).toContain('Question: When does my career become more stable?');
    expect(text).toContain('TECHNICAL BASIS');
    expect(text).toContain('10th lord Mercury');
    expect(text).toContain('Chapter 10');
    expect(text).toContain('INTERPRETATION');
    expect(text).toContain('PRACTICAL ACTIONS');
    expect(text).toContain('TRADITIONAL SUPPORTS');
    expect(text).toContain('FOLLOW-UP QUESTIONS');
    expect(text).toContain('Saved profile context: revision 4');
  });

  it('keeps legacy messages usable without inventing structured sections', () => {
    expect(askReportText({ ...INPUT, reading: null, fallbackContent: '**Legacy answer.**' })).toBe('Legacy answer.');
  });

  it('generates a real PDF blob in-browser', async () => {
    const pdf = askReportPdf(INPUT);
    expect(pdf.type).toBe('application/pdf');
    expect(pdf.size).toBeGreaterThan(10_000);
    const header = new TextDecoder().decode((await pdf.arrayBuffer()).slice(0, 8));
    expect(header.startsWith('%PDF-1.4')).toBeTrue();
  });
});
