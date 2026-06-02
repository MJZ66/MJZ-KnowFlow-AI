import { render, screen } from '@testing-library/react';
import MarkdownRenderer from '../MarkdownRenderer';

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
});
