import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Loader2, LogOut } from 'lucide-react';
import { useUserStore } from '../stores/userStore';

interface LogoutButtonProps {
  className?: string;
}

export default function LogoutButton({ className = 'btn-ghost p-2 text-red-400/90 hover:text-red-400' }: LogoutButtonProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const logout = useUserStore((s) => s.logout);
  const isLoggingOut = useUserStore((s) => s.isLoggingOut);

  const handleLogout = useCallback(async () => {
    if (isLoggingOut) return;
    await logout();
    navigate('/login', { replace: true });
  }, [isLoggingOut, logout, navigate]);

  return (
    <button
      type="button"
      data-testid="nav-logout"
      onClick={() => void handleLogout()}
      disabled={isLoggingOut}
      className={`${className} logout-btn transition-all duration-200 ${
        isLoggingOut ? 'opacity-80 scale-95 cursor-wait' : 'active:scale-90'
      }`}
      title={t('auth.logout')}
      aria-busy={isLoggingOut}
      aria-label={isLoggingOut ? t('auth.loggingOut') : t('auth.logout')}
    >
      {isLoggingOut ? (
        <Loader2 className="w-4 h-4 animate-spin" aria-hidden />
      ) : (
        <LogOut className="w-4 h-4" aria-hidden />
      )}
    </button>
  );
}
