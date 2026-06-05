import { Check, Circle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { PASSWORD_RULES } from '../utils/password';

interface Props {
  password: string;
  className?: string;
}

export default function PasswordRequirements({ password, className = '' }: Props) {
  const { t } = useTranslation();

  return (
    <div
      className={`rounded-lg border border-surface-200/80 bg-surface-50/80 dark:bg-surface-900/50 dark:border-surface-700/80 p-3 space-y-2 ${className}`.trim()}
      data-testid="password-requirements"
      aria-live="polite"
    >
      <p className="text-xs font-medium text-surface-500">{t('auth.passwordRulesTitle')}</p>
      <ul className="space-y-1.5">
        {PASSWORD_RULES.map((rule) => {
          const ok = password.length > 0 && rule.test(password);
          const pending = password.length === 0;
          return (
            <li
              key={rule.id}
              className={`flex items-center gap-2 text-xs transition-colors ${
                ok
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : pending
                    ? 'text-surface-500'
                    : 'text-amber-600 dark:text-amber-400'
              }`}
            >
              {ok ? (
                <Check className="w-3.5 h-3.5 shrink-0" aria-hidden />
              ) : (
                <Circle className="w-3 h-3 shrink-0 opacity-50" aria-hidden />
              )}
              {t(`auth.passwordRule.${rule.id}`)}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
