import { cleanPlainText, paragraphRuns, parseRuns } from './answer-text';

describe('cleanPlainText', () => {
  it('flattens bold/underline markers, headers, and bullets to plain prose', () => {
    const text = '# A header\n**Career Trajectory:** Your Mars is strong.\n- First point\n- Second point';
    const cleaned = cleanPlainText(text);
    expect(cleaned).not.toContain('*');
    expect(cleaned).not.toContain('#');
    expect(cleaned).toContain('Career Trajectory: Your Mars is strong.');
    expect(cleaned).toContain('• First point');
  });
});

describe('parseRuns', () => {
  it('splits a bold side-heading lead-in from the rest of the paragraph', () => {
    const runs = parseRuns('**Career Trajectory:** Your Mars is strong this year.');
    expect(runs).toEqual([
      { text: 'Career Trajectory:', bold: true },
      { text: ' Your Mars is strong this year.', bold: false },
    ]);
  });

  it('supports __underline__-style bold markers the same way', () => {
    const runs = parseRuns('__Timing:__ after March.');
    expect(runs).toEqual([
      { text: 'Timing:', bold: true },
      { text: ' after March.', bold: false },
    ]);
  });

  it('returns one plain run for text with no bold markers at all', () => {
    expect(parseRuns('Nothing bold here.')).toEqual([{ text: 'Nothing bold here.', bold: false }]);
  });

  it('handles multiple bold spans in the same line', () => {
    const runs = parseRuns('**Savings:** strong. **Risk:** manageable.');
    expect(runs).toEqual([
      { text: 'Savings:', bold: true },
      { text: ' strong. ', bold: false },
      { text: 'Risk:', bold: true },
      { text: ' manageable.', bold: false },
    ]);
  });
});

describe('paragraphRuns', () => {
  it('preserves a bold side-heading per paragraph instead of discarding the emphasis', () => {
    const text = '**Career Trajectory:** Your Mars is strong.\n\n**Timing:** after March.';
    const paragraphs = paragraphRuns(text);
    expect(paragraphs.length).toBe(2);
    expect(paragraphs[0][0]).toEqual({ text: 'Career Trajectory:', bold: true });
    expect(paragraphs[1][0]).toEqual({ text: 'Timing:', bold: true });
  });

  it('collapses an incidental single newline inside a paragraph, same as the plain-text split', () => {
    const runs = paragraphRuns('A sentence the model\nwrapped mid-line.\n\nA second paragraph.');
    expect(runs.length).toBe(2);
    expect(runs[0].map((run) => run.text).join('')).toBe('A sentence the model wrapped mid-line.');
  });

  it('produces no runs at all for empty input', () => {
    expect(paragraphRuns('')).toEqual([]);
  });
});
