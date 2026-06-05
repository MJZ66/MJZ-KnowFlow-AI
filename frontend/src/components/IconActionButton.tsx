import type { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

type Variant = 'ghost' | 'danger' | 'primary';

interface IconActionButtonProps {
  onClick: () => void;
  icon: ReactNode;
  title: string;
  pending?: boolean;
  disabled?: boolean;
  variant?: Variant;
  className?: string;
  testId?: string;
}

const variantClass: Record<Variant, string> = {
  ghost: 'btn-ghost p-2',
  danger: 'btn-ghost p-2 text-red-400/90 hover:text-red-400',
  primary: 'btn-primary p-2',
};

export default function IconActionButton({
  onClick,
  icon,
  title,
  pending = false,
  disabled = false,
  variant = 'ghost',
  className = '',
  testId,
}: IconActionButtonProps) {
  const isDisabled = disabled || pending;

  return (
    <button
      type="button"
      data-testid={testId}
      onClick={() => void onClick()}
      disabled={isDisabled}
      title={title}
      aria-busy={pending}
      className={`${variantClass[variant]} icon-action-btn transition-all duration-200 ${
        pending ? 'opacity-75 scale-95 cursor-wait' : 'active:scale-90'
      } ${className}`.trim()}
    >
      {pending ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> : icon}
    </button>
  );
}
