import { useTranslation } from 'react-i18next';
import type { DocumentStatus } from '../types';

const statusKey: Record<DocumentStatus, string> = {
  uploaded: 'document.status.uploaded',
  parsing: 'document.status.parsing',
  chunking: 'document.status.chunking',
  embedding: 'document.status.embedding',
  completed: 'document.status.completed',
  failed: 'document.status.failed',
};

const statusClass: Record<DocumentStatus, string> = {
  uploaded: 'bg-surface-700 text-surface-300',
  parsing: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  chunking: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  embedding: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  completed: 'bg-green-500/10 text-green-400 border-green-500/30',
  failed: 'bg-red-500/10 text-red-400 border-red-500/30',
};

export default function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  const { t } = useTranslation();
  const cls = statusClass[status] || statusClass.uploaded;
  const isAnimating = status === 'parsing' || status === 'chunking' || status === 'embedding';

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      {isAnimating && <span className="w-2 h-2 rounded-full bg-current animate-pulse" />}
      {t(statusKey[status] || status)}
    </span>
  );
}
