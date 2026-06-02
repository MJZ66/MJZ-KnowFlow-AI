import { useTranslation } from 'react-i18next';
import { useUserStore } from '../stores/userStore';

interface RoleGuardProps {
  roles?: string[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export default function RoleGuard({ roles, children, fallback }: RoleGuardProps) {
  const { t } = useTranslation();
  const user = useUserStore((s) => s.user);

  if (!user) return null;

  if (roles && !roles.includes(user.role)) {
    return <>{fallback || <p className="text-surface-400 text-sm">{t('common.noPermission')}</p>}</>;
  }

  return <>{children}</>;
}
