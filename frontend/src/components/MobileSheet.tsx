import type { ReactNode } from 'react';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface MobileSheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  side?: 'left' | 'bottom';
  testId?: string;
}

export default function MobileSheet({
  open,
  onClose,
  title,
  children,
  side = 'bottom',
  testId,
}: MobileSheetProps) {
  const { t } = useTranslation();

  if (!open) return null;

  const panelClass =
    side === 'left'
      ? 'fixed inset-y-0 left-0 w-[min(100%,20rem)] z-[80] flex flex-col bg-surface-50 dark:bg-surface-950 border-r border-surface-200 dark:border-surface-800 shadow-2xl animate-slide-in-left'
      : 'fixed inset-x-0 bottom-0 max-h-[75vh] z-[80] flex flex-col rounded-t-2xl bg-surface-50 dark:bg-surface-950 border-t border-surface-200 dark:border-surface-800 shadow-2xl animate-slide-in-up';

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-[70] bg-black/50 backdrop-blur-sm"
        aria-label={t('common.cancel')}
        onClick={onClose}
      />
      <div className={panelClass} data-testid={testId} role="dialog" aria-modal="true">
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-200 dark:border-surface-800 shrink-0">
          <h2 className="font-semibold text-surface-800 dark:text-surface-200">{title}</h2>
          <button type="button" onClick={onClose} className="btn-ghost p-1.5" aria-label={t('common.cancel')}>
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto">{children}</div>
      </div>
    </>
  );
}
