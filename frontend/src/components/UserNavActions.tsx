import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Settings, User, Wrench } from 'lucide-react';
import { useUserStore } from '../stores/userStore';
import LogoutButton from './LogoutButton';

/** Shared header actions: account, admin, logout. */
export default function UserNavActions() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useUserStore((s) => s.user);
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  return (
    <>
      <button
        type="button"
        data-testid="nav-setup"
        onClick={() => navigate('/setup')}
        className="btn-ghost p-2"
        title={t('setup.navTitle')}
      >
        <Wrench className="w-4 h-4" />
      </button>
      <button
        type="button"
        data-testid="nav-account"
        onClick={() => navigate('/account')}
        className="btn-ghost p-2"
        title={t('account.title')}
      >
        <User className="w-4 h-4" />
      </button>
      {isAdmin && (
        <button
          type="button"
          data-testid="nav-admin"
          onClick={() => navigate('/admin')}
          className="btn-ghost p-2"
          title={t('admin.title')}
        >
          <Settings className="w-4 h-4" />
        </button>
      )}
      <LogoutButton />
    </>
  );
}
