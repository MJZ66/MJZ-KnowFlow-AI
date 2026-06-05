import type { ReactNode } from 'react';
import { Shield, ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import LangSwitcher from './LangSwitcher';
import ThemeSwitcher from './ThemeSwitcher';

interface AdminShellProps {
  children: ReactNode;
  onBack: () => void;
}

export default function AdminShell({ children, onBack }: AdminShellProps) {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen page-bg">
      <header className="glass-panel sticky top-0 z-20 border-b border-surface-200/90 dark:border-surface-800/90 rounded-none">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button type="button" onClick={onBack} className="btn-ghost p-1.5 shrink-0" title={t('common.back')}>
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="w-9 h-9 rounded-xl bg-brand-500/15 border border-brand-500/25 flex items-center justify-center shrink-0">
              <Shield className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            </div>
            <div className="min-w-0">
              <h1 className="font-display text-lg font-semibold text-surface-900 dark:text-surface-100 truncate">
                {t('admin.title')}
              </h1>
              <p className="text-xs text-surface-500 hidden sm:block">{t('admin.subtitle')}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <ThemeSwitcher testId="admin-theme-switcher" />
            <LangSwitcher testId="admin-lang-switcher" />
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-8 animate-fade-in">{children}</main>
    </div>
  );
}
