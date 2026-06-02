import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import ReferencePanel, { isNoiseSectionTitle } from '../ReferencePanel';
import type { SSEReference } from '../../types';

const refs: SSEReference[] = [
  {
    source_filename: '中文测试文档.txt',
    document_id: 1,
    chunk_id: 10,
    chunk_index: 0,
    page_number: null,
    section_title: null,
    content_preview: 'PostgreSQL Redis ChromaDB',
    score: 0.9,
  },
  {
    source_filename: 'noise.txt',
    document_id: 2,
    chunk_id: 11,
    chunk_index: 1,
    page_number: null,
    section_title: 'docker compose up -d',
    content_preview: 'should hide section',
    score: 0.5,
  },
];

describe('isNoiseSectionTitle', () => {
  it('flags docker commands as noise', () => {
    expect(isNoiseSectionTitle('docker compose up -d')).toBe(true);
  });

  it('allows normal section titles', () => {
    expect(isNoiseSectionTitle('系统架构')).toBe(false);
  });
});

describe('ReferencePanel', () => {
  it('renders valid filename', () => {
    render(
      <I18nextProvider i18n={i18n}>
        <ReferencePanel references={refs} />
      </I18nextProvider>,
    );
    expect(screen.getByText('中文测试文档.txt')).toBeInTheDocument();
  });

  it('calls onReferenceClick when card clicked', () => {
    const onClick = vi.fn();
    render(
      <I18nextProvider i18n={i18n}>
        <ReferencePanel references={refs} onReferenceClick={onClick} />
      </I18nextProvider>,
    );
    fireEvent.click(screen.getByTestId('reference-card-0'));
    expect(onClick).toHaveBeenCalledWith(refs[0]);
  });
});
