import { useTranslation } from 'react-i18next';
import { MessageSquare, Plus, Trash2 } from 'lucide-react';
import type { ChatSession } from '../types';

interface Props {
  sessions: ChatSession[];
  currentSessionId: number | null;
  onSelect: (session: ChatSession) => void;
  onCreate: () => void;
  onDelete: (session: ChatSession) => void;
}

export default function SessionList({ sessions, currentSessionId, onSelect, onCreate, onDelete }: Props) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-800">
        <h3 className="text-sm font-semibold text-surface-300">{t('chat.sessions')}</h3>
        <button
          type="button"
          data-testid="chat-new-session"
          onClick={onCreate}
          className="btn-ghost p-1.5"
          title={t('chat.newSession')}
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 && (
          <p className="text-surface-500 text-sm text-center py-8">{t('chat.noSessions')}</p>
        )}
        {sessions.map((s) => (
          <div key={s.id} className={`group flex items-center rounded-lg transition-all duration-150 ${
            s.id === currentSessionId ? 'bg-brand-500/10 border border-brand-500/20' : 'hover:bg-surface-800 border border-transparent'
          }`}>
            <button onClick={() => onSelect(s)} className="flex items-center gap-2 flex-1 px-3 py-2 text-left min-w-0">
              <MessageSquare className="w-4 h-4 shrink-0 text-surface-500" />
              <span className="text-sm text-surface-300 truncate">{s.title}</span>
            </button>
            <button onClick={(e) => { e.stopPropagation(); onDelete(s); }}
              className="p-1.5 text-surface-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
              title={t('common.delete')}>
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
