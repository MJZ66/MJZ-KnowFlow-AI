import { useTranslation } from 'react-i18next';
import { BookOpen, Globe, Lock, Users, ArrowUpRight } from 'lucide-react';
import type { KnowledgeBase } from '../types';
import { format } from '../utils/date';

const visibilityIcons = { private: Lock, team: Users, public: Globe };

export default function KnowledgeBaseCard({
  kb,
  onClick,
  showOwner = false,
}: {
  kb: KnowledgeBase;
  onClick: () => void;
  showOwner?: boolean;
}) {
  const { t } = useTranslation();
  const Icon = visibilityIcons[kb.visibility] || Lock;

  return (
    <button type="button" onClick={onClick} className="card-interactive text-left w-full group cursor-pointer">
      <div className="flex items-start justify-between mb-4">
        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-brand-500/20 to-brand-800/10 border border-brand-500/25 flex items-center justify-center">
          <BookOpen className="w-5 h-5 text-brand-400" />
        </div>
        <span className="flex items-center gap-1 text-xs text-surface-400 bg-surface-100 dark:bg-surface-800/80 border border-surface-200 dark:border-surface-700 px-2.5 py-1 rounded-full">
          <Icon className="w-3 h-3" />
          {kb.publish_status === 'pending'
            ? t('kb.publishPending')
            : t(`kb.visibility.${kb.visibility}`)}
        </span>
      </div>
      <h3 className="text-surface-900 dark:text-surface-100 font-semibold text-lg mb-1.5 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors flex items-center gap-2">
        <span className="truncate">{kb.name}</span>
        <ArrowUpRight className="w-4 h-4 opacity-0 -translate-y-0.5 group-hover:opacity-100 group-hover:translate-y-0 transition-all shrink-0 text-brand-400" />
      </h3>
      {kb.description ? (
        <p className="text-surface-400 text-sm line-clamp-2 leading-relaxed">{kb.description}</p>
      ) : (
        <p className="text-surface-600 text-sm italic">{t('kb.noDescription')}</p>
      )}
      {showOwner && kb.owner_username && (
        <p className="text-xs text-surface-500 mt-2">{t('kb.owner', { name: kb.owner_username })}</p>
      )}
      <p className="text-surface-600 text-xs mt-3 font-mono">{format(kb.created_at)}</p>
    </button>
  );
}
