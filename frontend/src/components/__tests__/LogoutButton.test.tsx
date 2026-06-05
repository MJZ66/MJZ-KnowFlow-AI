import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LogoutButton from '../LogoutButton';
import { useUserStore } from '../../stores/userStore';

vi.mock('../../stores/userStore', () => ({
  useUserStore: vi.fn(),
}));

function renderLogout() {
  return render(
    <MemoryRouter>
      <LogoutButton />
    </MemoryRouter>,
  );
}

describe('LogoutButton', () => {
  const logout = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useUserStore).mockImplementation((selector) =>
      selector({
        logout,
        isLoggingOut: false,
      } as ReturnType<typeof useUserStore.getState>),
    );
  });

  it('shows spinner and calls logout when clicked', async () => {
    renderLogout();
    fireEvent.click(screen.getByTestId('nav-logout'));
    await waitFor(() => expect(logout).toHaveBeenCalledTimes(1));
  });

  it('is disabled while logging out', () => {
    vi.mocked(useUserStore).mockImplementation((selector) =>
      selector({
        logout,
        isLoggingOut: true,
      } as ReturnType<typeof useUserStore.getState>),
    );
    renderLogout();
    expect(screen.getByTestId('nav-logout')).toBeDisabled();
    expect(screen.getByTestId('nav-logout')).toHaveAttribute('aria-busy', 'true');
  });
});
