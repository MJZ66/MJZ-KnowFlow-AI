import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Moon, Sun } from 'lucide-react';
import { getSavedTheme, toggleTheme, type Theme } from '../theme';

interface Props {
  testId?: string;
}

export default function ThemeSwitcher({ testId = 'theme-switcher' }: Props) {
  const { t } = useTranslation();
  const [theme, setTheme] = useState<Theme>(() => getSavedTheme());

  useEffect(() => {
    const onChange = (e: Event) => {
      setTheme((e as CustomEvent<Theme>).detail);
    };
    window.addEventListener('knowflow-theme-change', onChange);
    return () => window.removeEventListener('knowflow-theme-change', onChange);
  }, []);

  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      data-testid={testId}
      onClick={() => setTheme(toggleTheme())}
      className="btn-ghost text-xs flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border border-surface-300/80 dark:border-surface-700/80 bg-white/70 dark:bg-surface-900/50"
      title={t('theme.switch')}
      aria-label={t('theme.switch')}
    >
      {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-brand-600" />}
      <span className="hidden sm:inline">{isDark ? t('theme.light') : t('theme.dark')}</span>
    </button>
  );
}
