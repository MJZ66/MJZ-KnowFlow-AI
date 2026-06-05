import type { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

interface SubmitButtonProps {
  loading: boolean;
  loadingLabel: string;
  label: string;
  className?: string;
  disabled?: boolean;
  icon?: ReactNode;
  testId?: string;
}

export default function SubmitButton({
  loading,
  loadingLabel,
  label,
  className = 'btn-primary w-full py-3',
  disabled = false,
  icon,
  testId,
}: SubmitButtonProps) {
  return (
    <button
      type="submit"
      data-testid={testId}
      disabled={loading || disabled}
      aria-busy={loading}
      className={`${className} transition-all duration-200 ${
        loading ? 'opacity-85 scale-[0.99] cursor-wait' : 'active:scale-[0.98]'
      }`}
    >
      {loading ? (
        <span className="inline-flex items-center justify-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
          {loadingLabel}
        </span>
      ) : (
        <span className="inline-flex items-center justify-center gap-2">
          {icon}
          {label}
        </span>
      )}
    </button>
  );
}
