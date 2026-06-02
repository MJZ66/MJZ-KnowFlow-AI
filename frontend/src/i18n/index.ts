import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import zhCN from './locales/zh-CN.json';
import enUS from './locales/en-US.json';

const LANG_KEY = 'knowflow_lang';

export function getSavedLanguage(): string {
  return localStorage.getItem(LANG_KEY) || 'zh-CN';
}

export function setLanguage(lang: string) {
  localStorage.setItem(LANG_KEY, lang);
  i18n.changeLanguage(lang);
}

i18n.use(initReactI18next).init({
  resources: {
    'zh-CN': { translation: zhCN },
    'en-US': { translation: enUS },
  },
  lng: getSavedLanguage(),
  fallbackLng: 'zh-CN',
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
