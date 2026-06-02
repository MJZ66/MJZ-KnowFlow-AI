import { useTranslation } from 'react-i18next';
import { BookOpen, Globe, Lock, Users } from 'lucide-react';
import type { KnowledgeBase } from '../types';
import { format } from '../utils/date';

const visibilityIcons = { private: Lock, team: Users, public: Globe };

export default function KnowledgeBaseCard({ kb, onClick }: { kb: KnowledgeBase; onClick: () => void }) {
  const { t } = useTranslation();
  const Icon = visibilityIcons[kb.visibility] || Lock;

  return (
    <button onClick={onClick} className="card text-left w-full group cursor-pointer">
      <div className="flex items-start justify-between mb-3">
        <div className="w-10 h-10 rounded-lg bg-brand-500/10 flex items-center justify-center">
          <BookOpen className="w-5 h-5 text-brand-400" />
        </div>
        <span className="flex items-center gap-1 text-xs text-surface-500 bg-surface-800 px-2 py-1 rounded-md">
          <Icon className="w-3 h-3" />
          {t(`kb.visibility.${kb.visibility}`)}
        </span>
      </div>
      <h3 className="text-surface-100 font-semibold text-lg mb-1 group-hover:text-brand-400 transition-colors">
        {kb.name}
      </h3>
      {kb.description && <p className="text-surface-400 text-sm line-clamp-2">{kb.description}</p>}
      <p className="text-surface-600 text-xs mt-3">{format(kb.created_at)}</p>
    </button>
  );
}
