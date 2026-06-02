import { create } from 'zustand';
import type { User, AuthTokens } from '../types';
import { api, setTokens, clearTokens } from '../api/client';

interface UserState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username: string) => Promise<void>;
  fetchMe: () => Promise<void>;
  logout: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,

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

  logout: () => {
    clearTokens();
    set({ user: null, isAuthenticated: false });
  },
}));
