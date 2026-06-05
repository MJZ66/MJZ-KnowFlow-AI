import { Waves } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface BrandMarkProps {
  size?: 'sm' | 'md' | 'lg';
  showName?: boolean;
  className?: string;
}

const sizes = {
  sm: { box: 'w-8 h-8', icon: 'w-4 h-4', title: 'text-lg' },
  md: { box: 'w-10 h-10', icon: 'w-5 h-5', title: 'text-xl' },
  lg: { box: 'w-12 h-12', icon: 'w-6 h-6', title: 'text-2xl' },
};

export default function BrandMark({ size = 'md', showName = true, className = '' }: BrandMarkProps) {
  const { t } = useTranslation();
  const s = sizes[size];
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div
        className={`${s.box} rounded-xl bg-gradient-to-br from-brand-500/25 to-brand-700/10 border border-brand-500/30 flex items-center justify-center shadow-glow`}
        aria-hidden
      >
        <Waves className={`${s.icon} text-brand-400`} />
      </div>
      {showName && (
        <span className={`${s.title} font-display font-semibold text-surface-900 dark:text-surface-100 tracking-tight`}>
          {t('app.name')}
        </span>
      )}
    </div>
  );
}
