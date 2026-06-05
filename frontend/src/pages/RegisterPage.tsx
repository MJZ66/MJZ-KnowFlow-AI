import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, User, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useUserStore } from '../stores/userStore';
import { parseApiError } from '../utils/error';
import AuthLayout from '../components/AuthLayout';
import PasswordRequirements from '../components/PasswordRequirements';
import { isPasswordValid } from '../utils/password';

export default function RegisterPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const register = useUserStore((s) => s.register);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!isPasswordValid(password)) {
      setError(t('auth.passwordInvalid'));
      return;
    }
    setLoading(true);
    try {
      await register(email, password, username);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title={t('auth.registerTitle')}
      footer={
        <>
          {t('auth.hasAccount')}{' '}
          <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium transition-colors">
            {t('auth.login')}
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/5 border border-red-500/20 rounded-lg p-3">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}
        <div>
          <label className="block text-sm text-surface-400 mb-1.5">{t('auth.username')}</label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-field pl-10"
              placeholder={t('auth.usernamePlaceholder')}
              required
              autoComplete="username"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm text-surface-400 mb-1.5">{t('auth.email')}</label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field pl-10"
              placeholder={t('auth.emailPlaceholder')}
              required
              autoComplete="email"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm text-surface-400 mb-1.5">{t('auth.password')}</label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field pl-10"
              placeholder={t('auth.passwordPlaceholder')}
              required
              minLength={6}
              autoComplete="new-password"
            />
          </div>
          <PasswordRequirements password={password} className="mt-2" />
        </div>
        <button type="submit" disabled={loading} className="btn-primary w-full py-3 mt-2">
          {loading ? t('auth.registering') : t('auth.registerButton')}
        </button>
      </form>
    </AuthLayout>
  );
}
