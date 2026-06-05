import { useTranslation } from 'react-i18next';
import { Loader2, MessageSquare, Plus, Trash2 } from 'lucide-react';
import type { ChatSession } from '../types';

interface Props {
  sessions: ChatSession[];
  currentSessionId: number | null;
  onSelect: (session: ChatSession) => void;
  onCreate: () => void;
  onDelete: (session: ChatSession) => void;
  creating?: boolean;
  deletingId?: number | null;
}

export default function SessionList({
  sessions,
  currentSessionId,
  onSelect,
  onCreate,
  onDelete,
  creating = false,
  deletingId = null,
}: Props) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-800">
        <h3 className="text-sm font-semibold text-surface-300">{t('chat.sessions')}</h3>
        <button
          type="button"
          data-testid="chat-new-session"
          onClick={() => void onCreate()}
          disabled={creating}
          aria-busy={creating}
          className={`btn-ghost p-1.5 transition-all duration-200 ${
            creating ? 'opacity-70 cursor-wait' : 'active:scale-90'
          }`}
          title={t('chat.newSession')}
        >
          {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 && (
          <p className="text-surface-500 text-sm text-center py-8">{t('chat.noSessions')}</p>
        )}
        {sessions.map((s) => (
          <div key={s.id} className={`group flex items-center rounded-xl transition-all duration-200 ${
            s.id === currentSessionId
              ? 'bg-brand-500/12 border border-brand-500/30 shadow-sm'
              : 'hover:bg-surface-800/80 border border-transparent'
          }`}>
            <button onClick={() => onSelect(s)} className="flex items-center gap-2 flex-1 px-3 py-2 text-left min-w-0">
              <MessageSquare className="w-4 h-4 shrink-0 text-surface-500" />
              <span className="text-sm text-surface-300 truncate">{s.title}</span>
            </button>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                void onDelete(s);
              }}
              disabled={deletingId === s.id}
              className={`p-1.5 text-surface-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all ${
                deletingId === s.id ? 'opacity-100 cursor-wait' : ''
              }`}
              title={t('common.delete')}
            >
              {deletingId === s.id ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Trash2 className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
