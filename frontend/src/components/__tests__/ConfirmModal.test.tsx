import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import ConfirmModal from '../ConfirmModal';
import { useConfirmStore } from '../../stores/confirmStore';

describe('ConfirmModal', () => {
  beforeEach(() => {
    useConfirmStore.setState({
      open: false,
      title: '',
      message: '',
      confirmLabel: undefined,
      cancelLabel: undefined,
      variant: 'default',
      resolve: null,
    });
  });

  it('calls close with true when confirm is clicked', () => {
    const resolve = vi.fn();
    useConfirmStore.setState({
      open: true,
      title: 'Delete item',
      message: 'Are you sure?',
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
      variant: 'danger',
      resolve,
    });

    render(
      <I18nextProvider i18n={i18n}>
        <ConfirmModal />
      </I18nextProvider>,
    );
    fireEvent.click(screen.getByTestId('confirm-modal-ok'));
    expect(resolve).toHaveBeenCalledWith(true);
  });
});
