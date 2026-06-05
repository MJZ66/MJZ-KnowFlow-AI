import { useTranslation } from 'react-i18next';

export interface DailyActivePoint {
  date: string;
  count: number;
}

interface Props {
  data: DailyActivePoint[];
  highlightToday?: number;
}

export default function AdminActivityChart({ data, highlightToday }: Props) {
  const { t } = useTranslation();
  const max = Math.max(1, ...data.map((d) => d.count));

  return (
    <div className="card !p-5" data-testid="admin-activity-chart">
      <div className="flex items-end justify-between gap-4 mb-6">
        <div>
          <h3 className="font-display text-lg font-semibold text-surface-900 dark:text-surface-100">
            {t('admin.dailyActive')}
          </h3>
          <p className="text-xs text-surface-500 mt-1">{t('admin.dailyActiveHint')}</p>
        </div>
        {highlightToday !== undefined && (
          <div className="text-right">
            <p className="text-2xl font-bold text-brand-600 dark:text-brand-400 tabular-nums">
              {highlightToday}
            </p>
            <p className="text-xs text-surface-500">{t('admin.dauToday')}</p>
          </div>
        )}
      </div>
      <div className="flex items-end gap-2 h-36">
        {data.map((point) => {
          const pct = Math.round((point.count / max) * 100);
          const isToday = data.length > 0 && point.date === data[data.length - 1]?.date;
          return (
            <div key={point.date} className="flex-1 flex flex-col items-center gap-2 min-w-0">
              <span className="text-[10px] text-surface-500 tabular-nums">{point.count}</span>
              <div
                className={`w-full rounded-t-md transition-all duration-500 admin-activity-bar ${
                  isToday ? 'admin-activity-bar-today' : ''
                }`}
                style={{ height: `${Math.max(pct, 4)}%` }}
                title={`${point.date}: ${point.count}`}
              />
              <span className="text-[10px] text-surface-500 truncate w-full text-center">
                {point.date.slice(5)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
