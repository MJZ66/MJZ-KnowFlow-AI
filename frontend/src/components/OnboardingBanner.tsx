import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BookOpen, MessageSquare, Upload, X } from 'lucide-react';

const STORAGE_KEY = 'knowflow_onboarding_dismissed';

export default function OnboardingBanner() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(() => localStorage.getItem(STORAGE_KEY) !== '1');

  if (!visible) return null;

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, '1');
    setVisible(false);
  };

  const steps = [
    { icon: BookOpen, text: t('onboarding.stepCreate') },
    { icon: Upload, text: t('onboarding.stepUpload') },
    { icon: MessageSquare, text: t('onboarding.stepChat') },
  ];

  return (
    <div
      className="mb-8 rounded-2xl border border-brand-500/25 bg-gradient-to-br from-brand-500/10 via-transparent to-surface-100/40 dark:to-surface-900/30 p-5 animate-fade-up"
      data-testid="onboarding-banner"
    >
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <p className="section-label mb-1">{t('onboarding.label')}</p>
          <h3 className="font-display text-lg font-semibold text-surface-900 dark:text-surface-100">
            {t('onboarding.title')}
          </h3>
          <p className="text-sm text-surface-500 mt-1">{t('onboarding.subtitle')}</p>
        </div>
        <button type="button" onClick={dismiss} className="btn-ghost p-1.5 shrink-0" aria-label={t('onboarding.dismiss')}>
          <X className="w-4 h-4" />
        </button>
      </div>
      <ol className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {steps.map(({ icon: Icon, text }, idx) => (
          <li
            key={idx}
            className="flex items-start gap-3 rounded-xl border border-surface-200/80 dark:border-surface-800/80 bg-white/50 dark:bg-surface-950/40 px-3 py-3"
          >
            <span className="w-7 h-7 rounded-lg bg-brand-500/15 border border-brand-500/25 flex items-center justify-center shrink-0 text-xs font-bold text-brand-600 dark:text-brand-400">
              {idx + 1}
            </span>
            <div className="min-w-0">
              <Icon className="w-4 h-4 text-brand-500 mb-1" />
              <p className="text-sm text-surface-700 dark:text-surface-300 leading-relaxed">{text}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
