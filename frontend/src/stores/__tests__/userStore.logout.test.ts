import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useUserStore } from '../userStore';

describe('userStore logout', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token');
    localStorage.setItem('refresh_token', 'test-refresh');
    useUserStore.setState({
      user: { id: 1, email: 'a@b.com', username: 'u', role: 'user', created_at: '' },
      isAuthenticated: true,
      isLoggingOut: false,
    });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    localStorage.clear();
    useUserStore.setState({
      user: null,
      isAuthenticated: false,
      isLoggingOut: false,
      isLoading: false,
    });
  });

  it('clears auth state after animation delay', async () => {
    const promise = useUserStore.getState().logout();
    expect(useUserStore.getState().isLoggingOut).toBe(true);
    await vi.advanceTimersByTimeAsync(400);
    await promise;
    expect(useUserStore.getState().isAuthenticated).toBe(false);
    expect(useUserStore.getState().user).toBeNull();
    expect(useUserStore.getState().isLoggingOut).toBe(false);
    expect(localStorage.getItem('access_token')).toBeNull();
  });
});
