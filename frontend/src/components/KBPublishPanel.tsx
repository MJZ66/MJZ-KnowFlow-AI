import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, Clock, CheckCircle2, XCircle } from 'lucide-react';
import type { KnowledgeBase } from '../types';
import { useUserStore } from '../stores/userStore';
import { useKBStore } from '../stores/kbStore';
import { parseApiError } from '../utils/error';

interface Props {
  kb: KnowledgeBase;
}

export default function KBPublishPanel({ kb }: Props) {
  const { t } = useTranslation();
  const user = useUserStore((s) => s.user);
  const requestPublish = useKBStore((s) => s.requestPublish);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const isOwner = user?.id === kb.user_id;
  const status = kb.publish_status || 'none';

  if (!isOwner || kb.visibility === 'public') return null;

  const handleRequest = async () => {
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await requestPublish(kb.id);
      setSuccess(t('kb.publishRequestSent'));
    } catch (err: unknown) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="mx-4 mt-3 mb-1 rounded-xl border border-surface-200 dark:border-surface-800 bg-surface-50/80 dark:bg-surface-900/50 p-4"
      data-testid="kb-publish-panel"
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center shrink-0">
          <Globe className="w-4 h-4 text-brand-600 dark:text-brand-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-surface-800 dark:text-surface-200">
            {t('kb.publishTitle')}
          </p>
          <p className="text-xs text-surface-500 mt-1 leading-relaxed">{t('kb.publishHint')}</p>

          {status === 'pending' && (
            <p className="mt-2 text-xs text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              {t('kb.publishPending')}
            </p>
          )}
          {status === 'rejected' && (
            <p className="mt-2 text-xs text-red-600 dark:text-red-400 flex items-center gap-1.5">
              <XCircle className="w-3.5 h-3.5" />
              {t('kb.publishRejected')}
              {kb.publish_review_note && `: ${kb.publish_review_note}`}
            </p>
          )}
          {status === 'approved' && (
            <p className="mt-2 text-xs text-brand-600 dark:text-brand-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {t('kb.publishApproved')}
            </p>
          )}
          {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
          {success && <p className="mt-2 text-xs text-brand-600 dark:text-brand-400">{success}</p>}

          {(status === 'none' || status === 'rejected') && (
            <button
              type="button"
              data-testid="kb-publish-request"
              disabled={loading}
              onClick={handleRequest}
              className="btn-primary mt-3 text-xs py-2 px-3"
            >
              {loading ? t('kb.publishSubmitting') : t('kb.publishSubmit')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
