/** Shared answer-text processing for the streamed Ask UI and the Copy/PDF
 * report — one place for the rules both surfaces need to agree on.
 *
 * The Balanced voice's own prompt deliberately allows this
 * (`astrospace/agents/domain_agent.py`'s `_REGISTER_BALANCED`: "Prose over
 * bullets; a header is fine if the answer is genuinely long"), so a model
 * answer's `interpretation` can legitimately contain markdown-style bold
 * side-headings — `"**Career Trajectory:** Your chart shows..."`. Every
 * renderer of that text previously stripped the `**` markers down to flat
 * prose with no substitute styling: the formatting signal was discarded,
 * not translated. This module is the one correct treatment, used by both
 * `ask-answer.component.ts` (the live streamed answer) and
 * `ask-report.ts` (Copy Answer and the PDF), so they cannot drift apart
 * the way `clean()`/`normaliseAnswerText()` already had before this file
 * existed — two independent copies of the same regex chain.
 */

export interface TextRun {
  text: string;
  bold: boolean;
}

function normalizeStructure(text: string): string {
  return String(text || '')
    .replace(/^\s{0,3}#{1,6}\s*/gm, '')
    .replace(/^\s*[-*]\s+/gm, '• ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/\s+([,.;:!?])/g, '$1')
    .trim();
}

/** Strips markdown structure (headers, bullets, whitespace) AND flattens
 * `**bold**`/`__bold__` markers to plain text — for contexts with no
 * rendering surface for emphasis: clipboard copy, text-to-speech, and the
 * plain-text fallback (`askReportText`, `readingParagraphs`, `sentences`). */
export function cleanPlainText(text: string): string {
  return normalizeStructure(
    String(text || '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/__(.*?)__/g, '$1'),
  );
}

/** Splits one already-structure-normalized line into alternating plain/bold
 * runs, preserving every character outside the `**...**`/`__...__` markers
 * exactly (including surrounding spaces, so words never fuse together). */
export function parseRuns(line: string): TextRun[] {
  const runs: TextRun[] = [];
  const pattern = /\*\*(.+?)\*\*|__(.+?)__/g;
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(line))) {
    if (match.index > cursor) runs.push({ text: line.slice(cursor, match.index), bold: false });
    const inner = match[1] ?? match[2] ?? '';
    if (inner) runs.push({ text: inner, bold: true });
    cursor = pattern.lastIndex;
  }
  if (cursor < line.length) runs.push({ text: line.slice(cursor), bold: false });
  return runs;
}

/** Splits raw model text into paragraphs, each as a run list ready to
 * render with emphasis preserved — the rich counterpart to a flattened
 * plain-text paragraph split. Paragraph boundaries are blank lines; a
 * single embedded newline inside one is treated as incidental wrapping
 * and joined with a space, matching `cleanPlainText`'s own paragraphing. */
export function paragraphRuns(text: string): TextRun[][] {
  return normalizeStructure(text)
    .split(/\n\s*\n+/)
    .map((paragraph) => paragraph.replace(/\s*\n\s*/g, ' ').trim())
    .filter(Boolean)
    .map(parseRuns);
}
