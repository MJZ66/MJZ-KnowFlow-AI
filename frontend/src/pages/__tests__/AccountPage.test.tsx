import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import AccountPage from '../AccountPage';

const changePassword = vi.fn();

vi.mock('../../stores/userStore', () => ({
  useUserStore: (selector: (s: { user: unknown; changePassword: typeof changePassword }) => unknown) =>
    selector({
      user: { id: 1, email: 'u@test.com', username: 'tester', role: 'user', created_at: '' },
      changePassword,
    }),
}));

function renderPage() {
  return render(
    <I18nextProvider i18n={i18n}>
      <MemoryRouter>
        <AccountPage />
      </MemoryRouter>
    </I18nextProvider>,
  );
}

describe('AccountPage', () => {
  beforeEach(() => {
    changePassword.mockReset();
    changePassword.mockResolvedValue(undefined);
  });

  it('shows password form and submits', async () => {
    renderPage();
    fireEvent.change(screen.getByTestId('account-current-password'), {
      target: { value: 'OldPass1!' },
    });
    fireEvent.change(screen.getByTestId('account-new-password'), {
      target: { value: 'NewPass2!' },
    });
    fireEvent.change(screen.getByTestId('account-confirm-password'), {
      target: { value: 'NewPass2!' },
    });
    fireEvent.click(screen.getByTestId('account-change-password-submit'));

    await waitFor(() => {
      expect(changePassword).toHaveBeenCalledWith('OldPass1!', 'NewPass2!');
    });
  });

  it('shows mismatch error when confirm differs', async () => {
    renderPage();
    fireEvent.change(screen.getByTestId('account-current-password'), {
      target: { value: 'OldPass1!' },
    });
    fireEvent.change(screen.getByTestId('account-new-password'), {
      target: { value: 'NewPass2!' },
    });
    fireEvent.change(screen.getByTestId('account-confirm-password'), {
      target: { value: 'OtherPass3!' },
    });
    fireEvent.submit(screen.getByTestId('account-password-form'));

    await waitFor(() => {
      expect(changePassword).not.toHaveBeenCalled();
      expect(screen.getByText(/不一致|do not match/i)).toBeInTheDocument();
    });
  });
});
