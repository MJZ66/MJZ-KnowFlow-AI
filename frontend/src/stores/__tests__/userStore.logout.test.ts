import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';

vi.mock('../../api/client', () => ({
  api: vi.fn().mockResolvedValue({ message: 'Logged out successfully.' }),
  clearLegacyTokens: vi.fn(),
  ensureCsrfToken: vi.fn().mockResolvedValue('test-csrf'),
  resetCsrfToken: vi.fn(),
}));

import { api, clearLegacyTokens, resetCsrfToken } from '../../api/client';
import { useUserStore } from '../userStore';

describe('userStore logout', () => {
  beforeEach(() => {
    useUserStore.setState({
      user: { id: 1, email: 'a@b.com', username: 'u', role: 'user', created_at: '' },
      isAuthenticated: true,
      isLoggingOut: false,
      authChecked: true,
    });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    useUserStore.setState({
      user: null,
      isAuthenticated: false,
      isLoggingOut: false,
      isLoading: false,
      authChecked: false,
    });
  });

  it('clears auth state and calls server logout after animation delay', async () => {
    const promise = useUserStore.getState().logout();
    expect(useUserStore.getState().isLoggingOut).toBe(true);
    await vi.advanceTimersByTimeAsync(400);
    await promise;
    expect(useUserStore.getState().isAuthenticated).toBe(false);
    expect(useUserStore.getState().user).toBeNull();
    expect(useUserStore.getState().isLoggingOut).toBe(false);
    expect(api).toHaveBeenCalledWith('/api/auth/logout', { method: 'POST' });
    expect(clearLegacyTokens).toHaveBeenCalled();
    expect(resetCsrfToken).toHaveBeenCalled();
  });
});
