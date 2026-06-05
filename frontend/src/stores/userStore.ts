import { create } from 'zustand';
import type { User, AuthTokens } from '../types';
import { api, setTokens, clearTokens } from '../api/client';
import { useKBStore } from './kbStore';
import { useChatStore } from './chatStore';

const LOGOUT_ANIMATION_MS = 380;

interface UserState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isLoggingOut: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username: string) => Promise<void>;
  fetchMe: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useUserStore = create<UserState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,
  isLoggingOut: false,

  login: async (email, password) => {
    const tokens = await api<AuthTokens>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    set({ isAuthenticated: true });
    // Fetch user info
    const user = await api<User>('/api/auth/me');
    set({ user });
  },

  register: async (email, password, username) => {
    const tokens = await api<AuthTokens>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, username }),
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    set({ isAuthenticated: true });
    const user = await api<User>('/api/auth/me');
    set({ user });
  },

  fetchMe: async () => {
    if (!localStorage.getItem('access_token')) return;
    set({ isLoading: true });
    try {
      const user = await api<User>('/api/auth/me');
      set({ user, isAuthenticated: true });
    } catch {
      clearTokens();
      set({ user: null, isAuthenticated: false });
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
    clearTokens();
    useChatStore.getState().reset();
    useKBStore.getState().reset();
    set({ user: null, isAuthenticated: false, isLoggingOut: false });
  },
}));
