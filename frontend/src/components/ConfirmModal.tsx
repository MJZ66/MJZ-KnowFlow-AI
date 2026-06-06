import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';
import { useConfirmStore } from '../stores/confirmStore';

export default function ConfirmModal() {
  const { t } = useTranslation();
  const { open, title, message, confirmLabel, cancelLabel, variant, close } = useConfirmStore();

  if (!open) return null;

  const isDanger = variant === 'danger';

  return (
    <div
      className="modal-backdrop fixed inset-0 z-[90] flex items-center justify-center bg-black/60 backdrop-blur-md p-4"
      role="dialog"
      aria-modal="true"
      data-testid="confirm-modal"
      onClick={() => close(false)}
    >
      <div
        className="modal-panel card w-full max-w-md shadow-glow border-brand-600/20"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-3 mb-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              isDanger
                ? 'bg-red-500/10 border border-red-500/25'
                : 'bg-brand-500/10 border border-brand-500/25'
            }`}
          >
            <AlertTriangle className={`w-5 h-5 ${isDanger ? 'text-red-400' : 'text-brand-400'}`} />
          </div>
          <div className="min-w-0">
            <h3 className="font-display text-lg font-semibold text-surface-100">{title}</h3>
            <p className="text-sm text-surface-400 mt-1 leading-relaxed">{message}</p>
          </div>
        </div>
        <div className="flex gap-3 justify-end pt-2">
          <button type="button" onClick={() => close(false)} className="btn-secondary">
            {cancelLabel ?? t('common.cancel')}
          </button>
          <button
            type="button"
            data-testid="confirm-modal-ok"
            onClick={() => close(true)}
            className={isDanger ? 'btn-danger' : 'btn-primary'}
          >
            {confirmLabel ?? t('common.confirm')}
          </button>
        </div>
      </div>
    </div>
  );
}
