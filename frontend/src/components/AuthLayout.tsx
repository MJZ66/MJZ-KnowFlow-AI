import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FileSearch, Layers, Sparkles } from 'lucide-react';
import BrandMark from './BrandMark';
import LangSwitcher from './LangSwitcher';
import ThemeSwitcher from './ThemeSwitcher';

interface AuthLayoutProps {
  title: string;
  children: ReactNode;
  footer: ReactNode;
}

const features = [
  { icon: FileSearch, key: 'app.featureUpload' },
  { icon: Layers, key: 'app.featureHybrid' },
  { icon: Sparkles, key: 'app.featureStream' },
] as const;

export default function AuthLayout({ title, children, footer }: AuthLayoutProps) {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen page-bg flex flex-col lg:flex-row">
      <aside className="hidden lg:flex lg:w-[44%] xl:w-[42%] flex-col justify-between p-12 border-r border-surface-200/90 dark:border-surface-800/80 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-950/40 via-transparent to-surface-950 pointer-events-none" />
        <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-brand-500/10 blur-3xl pointer-events-none" />
        <div className="relative z-10">
          <Link to="/login" className="inline-block">
            <BrandMark size="lg" />
          </Link>
          <p className="mt-8 font-display text-3xl xl:text-4xl font-semibold text-surface-900 dark:text-surface-100 leading-tight max-w-md">
            {t('app.heroTitle')}
          </p>
          <p className="mt-4 text-surface-400 text-lg max-w-sm leading-relaxed">{t('app.subtitle')}</p>
        </div>
        <ul className="relative z-10 space-y-4 mt-12">
          {features.map(({ icon: Icon, key }, i) => (
            <li
              key={key}
              className={`flex items-start gap-3 text-surface-300 animate-fade-up stagger-${i + 1}`}
            >
              <span className="w-9 h-9 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center shrink-0">
                <Icon className="w-4 h-4 text-brand-400" />
              </span>
              <span className="text-sm leading-relaxed pt-1.5 text-surface-600 dark:text-surface-300">{t(key)}</span>
            </li>
          ))}
        </ul>
      </aside>

      <main className="flex-1 flex flex-col justify-center px-6 py-10 lg:py-12">
        <div className="w-full max-w-md mx-auto animate-fade-up">
          <div className="flex items-center justify-between mb-8 lg:mb-10">
            <div className="lg:hidden">
              <BrandMark size="md" />
            </div>
            <div className="flex items-center gap-2">
              <ThemeSwitcher testId="auth-theme-switcher" />
              <LangSwitcher testId="auth-lang-switcher" />
            </div>
          </div>

          <div className="mb-6 lg:hidden">
            <p className="font-display text-xl font-semibold text-surface-800 dark:text-surface-200">{t('app.heroTitle')}</p>
          </div>

          <h1 className="font-display text-2xl font-semibold text-surface-900 dark:text-surface-100 mb-6">{title}</h1>

          <div className="card shadow-card !p-5 sm:!p-6">{children}</div>
          <div className="mt-6 text-center text-sm text-surface-500">{footer}</div>
        </div>
      </main>
    </div>
  );
}
