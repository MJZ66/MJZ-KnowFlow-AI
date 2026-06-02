import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import DocumentStatusBadge from '../DocumentStatusBadge';

function renderBadge(status: 'completed' | 'failed' | 'embedding') {
  return render(
    <I18nextProvider i18n={i18n}>
      <DocumentStatusBadge status={status} />
    </I18nextProvider>,
  );
}

describe('DocumentStatusBadge', () => {
  it('shows completed label', () => {
    renderBadge('completed');
    expect(screen.getByText(/已完成|Completed/i)).toBeInTheDocument();
  });

  it('shows failed label', () => {
    renderBadge('failed');
    expect(screen.getByText(/失败|Failed/i)).toBeInTheDocument();
  });

  it('shows embedding label', () => {
    renderBadge('embedding');
    expect(screen.getByText(/向量化|Embedding/i)).toBeInTheDocument();
  });
});
