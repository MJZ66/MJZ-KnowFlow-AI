import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Loader2, X, Globe } from 'lucide-react';
import { api } from '../../api/client';
import { parseApiError } from '../../utils/error';
import type { KBPublishRequest } from '../../types';
import { format } from '../../utils/date';

export default function AdminPublishApprovals() {
  const { t } = useTranslation();
  const [items, setItems] = useState<KBPublishRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actingId, setActingId] = useState<number | null>(null);
  const [actingAction, setActingAction] = useState<'approve' | 'reject' | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api<KBPublishRequest[]>('/api/admin/kb-publish-requests');
      setItems(data);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const review = async (kbId: number, action: 'approve' | 'reject') => {
    setActingId(kbId);
    setActingAction(action);
    setError('');
    try {
      await api(`/api/admin/kb-publish-requests/${kbId}/${action}`, { method: 'POST' });
      await load();
    } catch (err: unknown) {
      setError(parseApiError(err));
    } finally {
      setActingId(null);
      setActingAction(null);
    }
  };

  if (loading) {
    return (
      <div className="card p-8 space-y-3">
        {[1, 2].map((i) => (
          <div key={i} className="h-16 bg-surface-100 dark:bg-surface-800 rounded-lg animate-pulse" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="card p-12 text-center text-surface-500 text-sm" data-testid="admin-publish-empty">
        <Globe className="w-10 h-10 mx-auto mb-3 text-surface-400" />
        {t('admin.noPublishRequests')}
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="admin-publish-approvals">
      {error && (
        <p className="text-sm text-red-600 dark:text-red-400 bg-red-500/5 border border-red-500/20 rounded-lg p-3">
          {error}
        </p>
      )}
      {items.map((item) => (
        <div key={item.id} className="card !p-5 flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-surface-900 dark:text-surface-100 truncate">{item.name}</h4>
            <p className="text-sm text-surface-500 mt-1 line-clamp-2">{item.description || '—'}</p>
            <p className="text-xs text-surface-500 mt-2">
              {t('admin.publishBy', { user: item.owner_username, email: item.owner_email })}
              {item.publish_requested_at && (
                <> · {format(item.publish_requested_at)}</>
              )}
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              type="button"
              data-testid={`publish-approve-${item.id}`}
              disabled={actingId === item.id}
              onClick={() => void review(item.id, 'approve')}
              className={`btn-primary flex items-center gap-1.5 text-sm py-2 transition-all ${
                actingId === item.id ? 'opacity-80 cursor-wait' : 'active:scale-[0.98]'
              }`}
            >
              {actingId === item.id && actingAction === 'approve' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              {t('admin.approve')}
            </button>
            <button
              type="button"
              data-testid={`publish-reject-${item.id}`}
              disabled={actingId === item.id}
              onClick={() => void review(item.id, 'reject')}
              className={`btn-danger flex items-center gap-1.5 text-sm py-2 transition-all ${
                actingId === item.id ? 'opacity-80 cursor-wait' : 'active:scale-[0.98]'
              }`}
            >
              {actingId === item.id && actingAction === 'reject' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <X className="w-4 h-4" />
              )}
              {t('admin.reject')}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
