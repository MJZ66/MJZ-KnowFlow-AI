import { create } from 'zustand';
import type { KnowledgeBase, KBMember } from '../types';
import { api } from '../api/client';

export interface PaginatedKBList {
  items: KnowledgeBase[];
  total: number;
  skip: number;
  limit: number;
}

/** Accept paginated API or legacy array response. */
export function normalizeKBList(data: unknown): PaginatedKBList {
  if (Array.isArray(data)) {
    return { items: data, total: data.length, skip: 0, limit: data.length };
  }
  const p = data as PaginatedKBList;
  return {
    items: p.items ?? [],
    total: p.total ?? p.items?.length ?? 0,
    skip: p.skip ?? 0,
    limit: p.limit ?? p.items?.length ?? 0,
  };
}

interface KBState {
  kbs: KnowledgeBase[];
  kbTotal: number;
  kbSkip: number;
  kbLimit: number;
  currentKB: KnowledgeBase | null;
  members: KBMember[];
  isLoading: boolean;

  publicKbs: KnowledgeBase[];
  publicKbTotal: number;

  fetchKBs: (skip?: number, limit?: number) => Promise<PaginatedKBList>;
  fetchPublicKBs: (skip?: number, limit?: number) => Promise<PaginatedKBList>;
  fetchKB: (id: number) => Promise<KnowledgeBase>;
  createKB: (name: string, description: string, visibility?: string) => Promise<KnowledgeBase>;
  requestPublish: (id: number) => Promise<KnowledgeBase>;
  updateKB: (id: number, data: Partial<KnowledgeBase>) => Promise<void>;
  deleteKB: (id: number) => Promise<void>;
  fetchMembers: (kbId: number) => Promise<void>;
  addMember: (kbId: number, userId: number, role: string) => Promise<void>;
  removeMember: (kbId: number, userId: number) => Promise<void>;
  setCurrentKB: (kb: KnowledgeBase | null) => void;
  reset: () => void;
}

export const useKBStore = create<KBState>((set, get) => ({
  kbs: [],
  kbTotal: 0,
  kbSkip: 0,
  kbLimit: 12,
  publicKbs: [],
  publicKbTotal: 0,
  currentKB: null,
  members: [],
  isLoading: false,

  fetchKBs: async (skip = 0, limit = get().kbLimit) => {
    set({ isLoading: true });
    try {
      const raw = await api<unknown>(`/api/kbs?skip=${skip}&limit=${limit}`);
      const page = normalizeKBList(raw);
      set({
        kbs: page.items,
        kbTotal: page.total,
        kbSkip: page.skip,
        kbLimit: page.limit,
      });
      return page;
    } finally {
      set({ isLoading: false });
    }
  },

  fetchKB: async (id) => {
    const kb = await api<KnowledgeBase>(`/api/kbs/${id}`);
    set({ currentKB: kb });
    return kb;
  },

  fetchPublicKBs: async (skip = 0, limit = 50) => {
    const raw = await api<unknown>(`/api/kbs/public/catalog?skip=${skip}&limit=${limit}`);
    const page = normalizeKBList(raw);
    set({ publicKbs: page.items, publicKbTotal: page.total });
    return page;
  },

  createKB: async (name, description, visibility = 'private') => {
    const kb = await api<KnowledgeBase>('/api/kbs', {
      method: 'POST',
      body: JSON.stringify({ name, description, visibility }),
    });
    set((s) => ({
      kbs: [kb, ...s.kbs],
      kbTotal: s.kbTotal + 1,
    }));
    return kb;
  },

  updateKB: async (id, data) => {
    const kb = await api<KnowledgeBase>(`/api/kbs/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
    set((s) => ({
      kbs: s.kbs.map((k) => (k.id === id ? kb : k)),
      currentKB: s.currentKB?.id === id ? kb : s.currentKB,
    }));
  },

  requestPublish: async (id) => {
    const kb = await api<KnowledgeBase>(`/api/kbs/${id}/publish-request`, { method: 'POST' });
    set((s) => ({
      kbs: s.kbs.map((k) => (k.id === id ? kb : k)),
      currentKB: s.currentKB?.id === id ? kb : s.currentKB,
    }));
    return kb;
  },

  deleteKB: async (id) => {
    await api(`/api/kbs/${id}`, { method: 'DELETE' });
    set((s) => ({
      kbs: s.kbs.filter((k) => k.id !== id),
      kbTotal: Math.max(0, s.kbTotal - 1),
      currentKB: s.currentKB?.id === id ? null : s.currentKB,
    }));
  },

  fetchMembers: async (kbId) => {
    const members = await api<KBMember[]>(`/api/kbs/${kbId}/members`);
    set({ members });
  },

  addMember: async (kbId, userId, role) => {
    await api(`/api/kbs/${kbId}/members`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, role }),
    });
    await get().fetchMembers(kbId);
  },

  removeMember: async (kbId, userId) => {
    await api(`/api/kbs/${kbId}/members/${userId}`, { method: 'DELETE' });
    set((s) => ({
      members: s.members.filter((m) => m.user_id !== userId),
    }));
  },

  setCurrentKB: (kb) => set({ currentKB: kb }),

  reset: () =>
    set({
      kbs: [],
      kbTotal: 0,
      kbSkip: 0,
      publicKbs: [],
      publicKbTotal: 0,
      currentKB: null,
      members: [],
      isLoading: false,
    }),
}));
