import i18n from '../i18n';

export function format(dateStr: string): string {
  const d = new Date(dateStr);
  const locale = i18n.language === 'en-US' ? 'en-US' : 'zh-CN';
  return d.toLocaleDateString(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (mins < 1) return i18n.t('date.justNow');
  if (mins < 60) return i18n.t('date.minutesAgo', { count: mins });
  if (hours < 24) return i18n.t('date.hoursAgo', { count: hours });
  if (days < 30) return i18n.t('date.daysAgo', { count: days });
  return format(dateStr);
}
