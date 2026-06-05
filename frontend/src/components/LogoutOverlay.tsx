import { useTranslation } from 'react-i18next';
import { Loader2 } from 'lucide-react';
import { useUserStore } from '../stores/userStore';

export default function LogoutOverlay() {
  const { t } = useTranslation();
  const isLoggingOut = useUserStore((s) => s.isLoggingOut);

  if (!isLoggingOut) return null;

  return (
    <div
      className="logout-overlay fixed inset-0 z-[100] flex items-center justify-center bg-surface-950/40 backdrop-blur-sm"
      role="status"
      aria-live="polite"
      data-testid="logout-overlay"
    >
      <div className="logout-overlay-panel flex flex-col items-center gap-3 rounded-2xl border border-surface-700/60 bg-surface-900/90 px-8 py-6 shadow-glow">
        <Loader2 className="w-8 h-8 text-brand-400 animate-spin" aria-hidden />
        <p className="text-sm text-surface-200 font-medium">{t('auth.loggingOut')}</p>
      </div>
    </div>
  );
}
