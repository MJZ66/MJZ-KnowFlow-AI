import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';
import { useToastStore, type ToastVariant } from '../stores/toastStore';

const ICONS: Record<ToastVariant, typeof Info> = {
  info: Info,
  success: CheckCircle2,
  error: AlertCircle,
};

const STYLES: Record<ToastVariant, string> = {
  info: 'border-surface-300 bg-white/95 text-surface-800 dark:border-surface-700 dark:bg-surface-900/95 dark:text-surface-100',
  success: 'border-brand-500/30 bg-brand-500/5 text-brand-800 dark:text-brand-300',
  error: 'border-red-500/30 bg-red-500/5 text-red-700 dark:text-red-300',
};

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-[calc(100%-2rem)] sm:w-full pointer-events-none"
      aria-live="polite"
    >
      {toasts.map((item) => {
        const Icon = ICONS[item.variant];
        return (
          <div
            key={item.id}
            className={`pointer-events-auto flex items-start gap-2 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-md animate-fade-up ${STYLES[item.variant]}`}
            role="status"
          >
            <Icon className="w-4 h-4 shrink-0 mt-0.5" />
            <p className="text-sm flex-1 leading-relaxed">{item.message}</p>
            <button
              type="button"
              onClick={() => dismiss(item.id)}
              className="btn-ghost p-0.5 shrink-0 opacity-60 hover:opacity-100"
              aria-label="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
