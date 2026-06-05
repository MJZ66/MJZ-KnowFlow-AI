import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Lock, Mail, User, AlertCircle, CheckCircle2 } from 'lucide-react';
import AppShell from '../components/AppShell';
import UserNavActions from '../components/UserNavActions';
import SubmitButton from '../components/SubmitButton';
import { useUserStore } from '../stores/userStore';
import { parseApiError } from '../utils/error';

export default function AccountPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useUserStore((s) => s.user);
  const changePassword = useUserStore((s) => s.changePassword);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword.length < 6) {
      setError(t('account.passwordTooShort'));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t('account.passwordMismatch'));
      return;
    }
    if (currentPassword === newPassword) {
      setError(t('account.passwordSame'));
      return;
    }

    setLoading(true);
    try {
      await changePassword(currentPassword, newPassword);
      setSuccess(t('account.passwordChanged'));
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: unknown) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell
      userLabel={user?.username}
      actions={
        <>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="btn-secondary text-sm"
          >
            {t('common.back')}
          </button>
          <UserNavActions />
        </>
      }
    >
      <div className="max-w-lg mx-auto">
        <p className="section-label mb-2">{t('account.title')}</p>
        <h2 className="font-display text-2xl font-semibold text-surface-900 dark:text-surface-100 mb-2">
          {t('account.title')}
        </h2>
        <p className="text-surface-500 text-sm mb-8">{t('account.subtitle')}</p>

        <div className="card mb-6 space-y-3">
          <div className="flex items-center gap-3 text-sm">
            <User className="w-4 h-4 text-surface-500 shrink-0" />
            <span className="text-surface-500">{t('auth.username')}</span>
            <span className="text-surface-800 dark:text-surface-200 font-medium ml-auto">{user?.username}</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <Mail className="w-4 h-4 text-surface-500 shrink-0" />
            <span className="text-surface-500">{t('auth.email')}</span>
            <span className="text-surface-800 dark:text-surface-200 font-medium ml-auto truncate">{user?.email}</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4" data-testid="account-password-form">
          <h3 className="font-semibold text-surface-800 dark:text-surface-200 flex items-center gap-2">
            <Lock className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            {t('account.changePassword')}
          </h3>

          {error && (
            <div className="flex items-start gap-2 text-red-600 dark:text-red-400 text-sm bg-red-500/5 border border-red-500/20 rounded-lg p-3">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="flex items-start gap-2 text-brand-700 dark:text-brand-400 text-sm bg-brand-500/5 border border-brand-500/20 rounded-lg p-3">
              <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{success}</span>
            </div>
          )}

          <div>
            <label className="block text-sm text-surface-500 mb-1.5">{t('account.currentPassword')}</label>
            <input
              type="password"
              data-testid="account-current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="input-field"
              placeholder={t('account.currentPasswordPlaceholder')}
              required
              autoComplete="current-password"
            />
          </div>
          <div>
            <label className="block text-sm text-surface-500 mb-1.5">{t('account.newPassword')}</label>
            <input
              type="password"
              data-testid="account-new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input-field"
              placeholder={t('auth.passwordPlaceholder')}
              required
              minLength={6}
              autoComplete="new-password"
            />
          </div>
          <div>
            <label className="block text-sm text-surface-500 mb-1.5">{t('account.confirmPassword')}</label>
            <input
              type="password"
              data-testid="account-confirm-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input-field"
              placeholder={t('account.confirmPasswordPlaceholder')}
              required
              minLength={6}
              autoComplete="new-password"
            />
          </div>

          <SubmitButton
            testId="account-change-password-submit"
            loading={loading}
            loadingLabel={t('account.saving')}
            label={t('account.savePassword')}
            className="btn-primary w-full py-3"
          />
        </form>
      </div>
    </AppShell>
  );
}
