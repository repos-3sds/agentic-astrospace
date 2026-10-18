import { Pipe, PipeTransform } from '@angular/core';
import { Marked } from 'marked';

const escapeHtml = (text: string): string =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/**
 * Markdown from the reading agents, as HTML for `[innerHTML]`.
 *
 * The text is model output, so it is not trusted (security audit S6): raw
 * HTML in it is shown as text rather than parsed, and the result goes through
 * Angular's own sanitizer instead of `bypassSecurityTrustHtml`, which strips
 * event handlers and `javascript:` links if anything slips past marked.
 */
const markdown = new Marked({
  renderer: {
    html: ({ text }) => escapeHtml(text),
  },
});

@Pipe({ name: 'markdown' })
export class MarkdownPipe implements PipeTransform {
  transform(value?: string | null): string {
    if (!value) return '';
    return markdown.parse(value, { async: false }) as string;
  }
}
