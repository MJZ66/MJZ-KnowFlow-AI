import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, ArrowRight, X } from 'lucide-react';
import { api } from '../api/client';

const DISMISS_KEY = 'knowflow_setup_alert_dismissed';

interface SetupStatus {
  overall_ok: boolean;
  ready_for_chat: boolean;
}

export default function SetupAlertBanner() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem(DISMISS_KEY) === '1');

  useEffect(() => {
    let cancelled = false;
    api<SetupStatus>('/api/setup/status')
      .then((res) => {
        if (!cancelled) setStatus(res);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  if (dismissed || !status || status.overall_ok) return null;

  return (
    <div
      className="mb-6 rounded-2xl border border-amber-500/35 bg-gradient-to-r from-amber-500/10 via-transparent to-brand-500/5 p-4 animate-fade-up"
      data-testid="setup-alert-banner"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-surface-900 dark:text-surface-100">
            {status.ready_for_chat ? t('setup.bannerWarn') : t('setup.bannerError')}
          </p>
          <p className="text-sm text-surface-500 mt-1">{t('setup.bannerHint')}</p>
          <button
            type="button"
            data-testid="setup-alert-open"
            onClick={() => navigate('/setup')}
            className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-600 dark:text-brand-400 hover:underline"
          >
            {t('setup.openGuide')}
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
        <button
          type="button"
          onClick={() => {
            sessionStorage.setItem(DISMISS_KEY, '1');
            setDismissed(true);
          }}
          className="btn-ghost p-1.5 shrink-0"
          aria-label={t('onboarding.dismiss')}
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
