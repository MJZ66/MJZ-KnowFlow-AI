import { create } from 'zustand';
import type { ChatSession, ChatMessage, SSEReference, RetrievalStats } from '../types';
import { api, streamRequest } from '../api/client';
import i18n from '../i18n';
import { parseApiError } from '../utils/error';

interface ChatState {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  streamContent: string;
  references: SSEReference[];
  streamError: string | null;
  retrievalStatus: string;
  retrievalStats: import('../types').RetrievalStats | null;
  abortController: AbortController | null;

  fetchSessions: (kbId: number) => Promise<void>;
  createSession: (kbId: number, title?: string) => Promise<ChatSession>;
  deleteSession: (sessionId: number) => Promise<void>;
  setCurrentSession: (session: ChatSession | null) => void;
  fetchMessages: (sessionId: number) => Promise<void>;
  sendMessage: (sessionId: number, content: string, topK?: number) => Promise<void>;
  stopStreaming: () => void;
  clearStreamState: () => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  currentSession: null,
  messages: [],
  isStreaming: false,
  streamContent: '',
  references: [],
  streamError: null,
  retrievalStatus: '',
  retrievalStats: null,
  abortController: null,

  fetchSessions: async (kbId) => {
    const sessions = await api<ChatSession[]>(`/api/kbs/${kbId}/chat/sessions`);
    set({ sessions });
  },

  createSession: async (kbId, title) => {
    const session = await api<ChatSession>(`/api/kbs/${kbId}/chat/sessions`, {
      method: 'POST',
      body: JSON.stringify({ title: title || 'New Chat' }),
    });
    set((s) => ({ sessions: [session, ...s.sessions], currentSession: session }));
    return session;
  },

  deleteSession: async (sessionId) => {
    await api(`/api/chat/sessions/${sessionId}`, { method: 'DELETE' });
    set((s) => ({
      sessions: s.sessions.filter((sess) => sess.id !== sessionId),
      currentSession: s.currentSession?.id === sessionId ? null : s.currentSession,
      messages: s.currentSession?.id === sessionId ? [] : s.messages,
    }));
  },

  setCurrentSession: (session) => {
    set({ currentSession: session, messages: [], references: [], streamContent: '', retrievalStatus: '', retrievalStats: null });
  },

  fetchMessages: async (sessionId) => {
    const messages = await api<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`);
    set({ messages });
  },

  sendMessage: async (sessionId, content, topK = 5) => {
    const abortController = new AbortController();

    // Add user message to local state immediately
    const userMsg: ChatMessage = {
      id: Date.now(),
      session_id: sessionId,
      user_id: 0,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    set({
      isStreaming: true,
      streamContent: '',
      references: [],
      streamError: null,
      retrievalStatus: i18n.t('chat.retrieving'),
      retrievalStats: null,
      abortController,
      messages: [...get().messages, userMsg],
    });

    let fullContent = '';
    let refs: SSEReference[] = [];

    try {
      const response = await streamRequest(
        `/api/chat/sessions/${sessionId}/stream`,
        { content, top_k: topK },
        abortController.signal
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(
          err.message
            ? JSON.stringify({ code: err.code, message: err.message, message_en: err.message_en })
            : (err.detail || `Stream error: ${response.status}`),
        );
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let eventType = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr);
              switch (eventType) {
                case 'retrieval_start':
                  set({ retrievalStatus: i18n.t('chat.retrieving') });
                  break;
                case 'retrieval_done': {
                  const stats: RetrievalStats = {
                    mode: data.mode,
                    raw_count: data.raw_count,
                    valid_count: data.valid_count,
                    reranked_count: data.reranked_count,
                    count: data.count,
                    cached: data.cached,
                  };
                  set({
                    retrievalStatus: i18n.t('chat.retrieved', { count: data.count ?? 0 }),
                    retrievalStats: stats,
                  });
                  break;
                }
                case 'token':
                  set({ retrievalStatus: '' });
                  fullContent += data.content || '';
                  set({ streamContent: fullContent });
                  break;
                case 'references':
                  refs = data;
                  set({ references: refs });
                  break;
                case 'done':
                  if (data.content) fullContent = data.content;
                  if (data.references) refs = data.references;
                  set({ streamContent: fullContent, references: refs });
                  break;
                case 'error':
                  set({ streamError: data.message || 'Unknown error' });
                  break;
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        // User cancelled
      } else {
        set({ streamError: parseApiError(err) });
      }
    } finally {
      // Add assistant message to local state
      if (fullContent) {
        const assistantMsg: ChatMessage = {
          id: Date.now() + 1,
          session_id: sessionId,
          user_id: 0,
          role: 'assistant',
          content: fullContent,
          created_at: new Date().toISOString(),
        };
        set((s) => ({
          messages: [...s.messages, assistantMsg],
          isStreaming: false,
          retrievalStatus: '',
          abortController: null,
        }));
      } else {
        set({ isStreaming: false, retrievalStatus: '', abortController: null });
      }
    }
  },

  stopStreaming: () => {
    const { abortController } = get();
    if (abortController) {
      abortController.abort();
    }
  },

  clearStreamState: () => {
    set({
      streamContent: '',
      references: [],
      streamError: null,
      retrievalStatus: '',
      retrievalStats: null,
      isStreaming: false,
    });
  },

  reset: () => {
    const { abortController } = get();
    if (abortController) abortController.abort();
    set({
      sessions: [],
      currentSession: null,
      messages: [],
      isStreaming: false,
      streamContent: '',
      references: [],
      streamError: null,
      retrievalStatus: '',
      retrievalStats: null,
      abortController: null,
    });
  },
}));
