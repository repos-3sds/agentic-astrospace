import { MarkdownPipe } from './markdown.pipe';

describe('MarkdownPipe', () => {
  const pipe = new MarkdownPipe();

  it('renders markdown', () => {
    expect(pipe.transform('**Steady** day')).toContain('<strong>Steady</strong>');
  });

  it('shows raw HTML from a model as text instead of running it', () => {
    const html = pipe.transform('Hello <img src=x onerror="alert(1)"> there');
    expect(html).not.toContain('<img');
    expect(html).toContain('&lt;img');
  });

  it('shows a raw HTML block as text', () => {
    expect(pipe.transform('<script>alert(1)</script>')).not.toContain('<script>');
  });
});
