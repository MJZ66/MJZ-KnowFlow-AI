import { render, screen } from '@testing-library/react';
import MarkdownRenderer, { renderMarkdown, safeHref } from '../MarkdownRenderer';

describe('MarkdownRenderer', () => {
  it('renders bold as strong', () => {
    const { container } = render(<MarkdownRenderer content="**bold text**" />);
    expect(container.querySelector('strong')).not.toBeNull();
    expect(screen.getByText('bold text')).toBeInTheDocument();
  });

  it('renders list items', () => {
    const { container } = render(<MarkdownRenderer content="- item one\n- item two" />);
    expect(container.querySelectorAll('li').length).toBeGreaterThanOrEqual(1);
  });

  it('renders inline code', () => {
    const { container } = render(<MarkdownRenderer content="use `npm run dev`" />);
    expect(container.querySelector('code')).not.toBeNull();
  });

  it('blocks javascript: links', () => {
    const html = renderMarkdown('[click me](javascript:alert(1))');
    expect(html).not.toContain('javascript:');
    expect(html).toContain('click me');
    expect(html).not.toContain('<a ');
  });

  it('allows https links with safe attributes', () => {
    const html = renderMarkdown('[docs](https://example.com/path)');
    expect(html).toContain('href="https://example.com/path"');
    expect(html).toContain('rel="noopener noreferrer"');
  });

  it('rejects data: URLs', () => {
    expect(safeHref('data:text/html,<script>alert(1)</script>')).toBeNull();
  });
});
