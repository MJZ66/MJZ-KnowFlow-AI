import type { ReactNode } from 'react';
import { ArrowLeft } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ThemeSwitcher from './ThemeSwitcher';
import LangSwitcher from './LangSwitcher';
import UserNavActions from './UserNavActions';

interface AppPageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  onBack: () => void;
  backPending?: boolean;
  actions?: ReactNode;
  showUserNav?: boolean;
  themeTestId?: string;
  langTestId?: string;
}

export default function AppPageHeader({
  title,
  subtitle,
  icon,
  onBack,
  backPending = false,
  actions,
  showUserNav = true,
  themeTestId,
  langTestId,
}: AppPageHeaderProps) {
  const { t } = useTranslation();

  return (
    <header className="app-page-header glass-panel sticky top-0 z-20 border-b border-surface-200/90 dark:border-surface-800/90 rounded-none shrink-0">
      <div className="h-14 px-4 sm:px-6 flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          disabled={backPending}
          className={`btn-ghost p-1.5 shrink-0 transition-all duration-200 ${
            backPending ? 'opacity-60 cursor-wait' : 'active:scale-90'
          }`}
          title={t('common.back')}
          data-testid="page-header-back"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>

        {icon && (
          <div className="w-9 h-9 rounded-xl bg-brand-500/12 border border-brand-500/25 flex items-center justify-center shrink-0 shadow-sm">
            {icon}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <h1 className="font-display font-semibold text-surface-900 dark:text-surface-100 truncate text-base sm:text-lg leading-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="text-xs text-surface-500 truncate hidden sm:block">{subtitle}</p>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {actions}
          <ThemeSwitcher testId={themeTestId} />
          <LangSwitcher testId={langTestId} />
          {showUserNav && <UserNavActions />}
        </div>
      </div>
    </header>
  );
}
