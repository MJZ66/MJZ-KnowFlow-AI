import { useTranslation } from 'react-i18next';
import { setLanguage, getSavedLanguage } from '../i18n';
import { Languages } from 'lucide-react';

interface Props {
  /** Override default data-testid for page-specific e2e selectors. */
  testId?: string;
}

export default function LangSwitcher({ testId = 'lang-switcher' }: Props) {
  const { t, i18n } = useTranslation();
  const currentLang = i18n.language || getSavedLanguage();

  const toggle = () => {
    const next = currentLang === 'zh-CN' ? 'en-US' : 'zh-CN';
    setLanguage(next);
  };

  return (
    <button
      type="button"
      data-testid={testId}
      onClick={toggle}
      className="btn-ghost text-xs flex items-center gap-1.5 px-2.5 py-1.5"
      title={t('lang.switch')}
    >
      <Languages className="w-3.5 h-3.5" />
      <span>{currentLang === 'zh-CN' ? 'EN' : '中文'}</span>
    </button>
  );
}
