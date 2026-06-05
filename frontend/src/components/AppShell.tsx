import type { ReactNode } from 'react';
import BrandMark from './BrandMark';
import LangSwitcher from './LangSwitcher';
import ThemeSwitcher from './ThemeSwitcher';

interface AppShellProps {
  children: ReactNode;
  userLabel?: string;
  actions?: ReactNode;
}

export default function AppShell({ children, userLabel, actions }: AppShellProps) {
  return (
    <div className="min-h-screen page-bg">
      <header className="glass-panel sticky top-0 z-20 border-b border-surface-200/90 dark:border-surface-800/90 mx-0">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <BrandMark size="sm" />
          <div className="flex items-center gap-2">
            <ThemeSwitcher />
            <LangSwitcher />
            {userLabel && (
              <span className="hidden sm:inline text-sm text-surface-500 dark:text-surface-400 px-3 py-1 rounded-full bg-surface-100 border border-surface-200 dark:bg-surface-800/60 dark:border-surface-700/80">
                {userLabel}
              </span>
            )}
            {actions}
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
    </div>
  );
}
