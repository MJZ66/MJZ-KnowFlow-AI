import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Brain, Mail, Lock, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useUserStore } from '../stores/userStore';
import { parseApiError } from '../utils/error';
import LangSwitcher from '../components/LangSwitcher';

export default function LoginPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const login = useUserStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: unknown) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-950 p-4">
      <div className="w-full max-w-md">
        <div className="text-right mb-4">
          <LangSwitcher />
        </div>

        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center">
              <Brain className="w-7 h-7 text-brand-400" />
            </div>
            <h1 className="text-2xl font-bold text-surface-100">{t('app.name')}</h1>
          </div>
          <p className="text-surface-500">{t('auth.loginTitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4">
          {error && (
            <div className="flex items-start gap-2 text-red-400 text-sm bg-red-500/5 border border-red-500/20 rounded-lg p-3">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-sm text-surface-400 mb-1.5">{t('auth.email')}</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
              <input
                type="email" value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field pl-10"
                placeholder={t('auth.emailPlaceholder')} required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-surface-400 mb-1.5">{t('auth.password')}</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
              <input
                type="password" value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field pl-10"
                placeholder={t('auth.passwordPlaceholder')} required minLength={6}
              />
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full py-3">
            {loading ? t('auth.loggingIn') : t('auth.loginButton')}
          </button>

          <p className="text-center text-sm text-surface-500">
            {t('auth.noAccount')}{' '}
            <Link to="/register" className="text-brand-400 hover:text-brand-300 transition-colors">
              {t('auth.register')}
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
