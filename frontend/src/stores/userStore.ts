import { create } from 'zustand';
import type { User } from '../types';
import { api, clearLegacyTokens, ensureCsrfToken, resetCsrfToken } from '../api/client';
import { useKBStore } from './kbStore';
import { useChatStore } from './chatStore';

const LOGOUT_ANIMATION_MS = 380;

interface UserState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isLoggingOut: boolean;
  authChecked: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username: string) => Promise<void>;
  fetchMe: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => Promise<void>;
}

clearLegacyTokens();

export const useUserStore = create<UserState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  isLoggingOut: false,
  authChecked: false,

  login: async (email, password) => {
    await ensureCsrfToken();
    await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    await ensureCsrfToken(true);
    const user = await api<User>('/api/auth/me');
    set({ user, isAuthenticated: true, authChecked: true });
  },

  register: async (email, password, username) => {
    await ensureCsrfToken();
    await api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, username }),
    });
    await ensureCsrfToken(true);
    const user = await api<User>('/api/auth/me');
    set({ user, isAuthenticated: true, authChecked: true });
  },

  fetchMe: async () => {
    set({ isLoading: true });
    try {
      const user = await api<User>('/api/auth/me');
      set({ user, isAuthenticated: true, authChecked: true });
    } catch {
      clearLegacyTokens();
      set({ user: null, isAuthenticated: false, authChecked: true });
    } finally {
      set({ isLoading: false });
    }
  },

  changePassword: async (currentPassword, newPassword) => {
    await api<{ message: string }>('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
  },

  logout: async () => {
    const { isLoggingOut } = useUserStore.getState();
    if (isLoggingOut) return;
    set({ isLoggingOut: true });
    await new Promise((resolve) => setTimeout(resolve, LOGOUT_ANIMATION_MS));
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch {
      // Still clear local state if server unreachable
    }
    clearLegacyTokens();
    resetCsrfToken();
    useChatStore.getState().reset();
    useKBStore.getState().reset();
    set({ user: null, isAuthenticated: false, isLoggingOut: false, authChecked: true });
  },
}));
