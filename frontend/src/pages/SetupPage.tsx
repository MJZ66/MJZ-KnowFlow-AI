import { useCallback, useEffect, useState, type ComponentType } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sparkles,
  Server,
  Brain,
  Image as ImageIcon,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import AppShell from '../components/AppShell';
import UserNavActions from '../components/UserNavActions';
import { useUserStore } from '../stores/userStore';
import { api } from '../api/client';
import { parseApiError } from '../utils/error';

interface SetupIssue {
  code: string;
  severity: string;
  message_zh: string;
  message_en: string;
}

interface SetupStatus {
  overall_ok: boolean;
  ready_for_chat: boolean;
  llm: { provider: string; model: string; configured: boolean; api_base: string };
  deepseek: { configured: boolean; api_base: string; usage_hint: string };
  embedding: { provider: string; vector_provider: string; dim: number };
  task_backend: string;
  ocr: { enabled: boolean; languages: string };
  metrics_enabled: boolean;
  issues: SetupIssue[];
  readiness: {
    status: string;
    checks: Record<string, { status: string; detail?: string }>;
  };
}

function StatusIcon({ ok, warn }: { ok: boolean; warn?: boolean }) {
  if (ok) return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
  if (warn) return <AlertTriangle className="w-5 h-5 text-amber-400" />;
  return <XCircle className="w-5 h-5 text-red-400" />;
}

export default function SetupPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const user = useUserStore((s) => s.user);
  const [data, setData] = useState<SetupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api<SetupStatus>('/api/setup/status');
      setData(res);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const isZh = i18n.language.startsWith('zh');
  const issueMessage = (issue: SetupIssue) => (isZh ? issue.message_zh : issue.message_en);

  return (
    <AppShell userLabel={user?.username} actions={<UserNavActions />}>
      <div className="max-w-3xl mx-auto">
        <div className="setup-hero mb-10 animate-fade-up">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-label mb-2">{t('setup.label')}</p>
              <h1 className="font-display text-3xl sm:text-4xl font-semibold text-surface-900 dark:text-surface-50 tracking-tight">
                {t('setup.title')}
              </h1>
              <p className="text-surface-500 mt-3 text-base leading-relaxed max-w-xl">
                {t('setup.subtitle')}
              </p>
            </div>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="btn-ghost p-2.5 shrink-0 rounded-xl border border-surface-200 dark:border-surface-700"
              title={t('setup.refresh')}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {loading && !data && (
          <div className="flex items-center justify-center gap-2 py-20 text-surface-400">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>{t('setup.loading')}</span>
          </div>
        )}

        {error && (
          <p className="text-center text-red-400 py-8">{error}</p>
        )}

        {data && (
          <div className="space-y-6">
            <div
              className={`setup-status-banner rounded-2xl border p-5 animate-fade-up ${
                data.overall_ok
                  ? 'border-emerald-500/30 bg-emerald-500/5'
                  : 'border-amber-500/30 bg-amber-500/5'
              }`}
              data-testid="setup-overall-status"
            >
              <div className="flex items-center gap-3">
                <StatusIcon ok={data.overall_ok} warn={!data.overall_ok && data.ready_for_chat} />
                <div>
                  <p className="font-semibold text-surface-900 dark:text-surface-100">
                    {data.overall_ok ? t('setup.allReady') : t('setup.needsAttention')}
                  </p>
                  <p className="text-sm text-surface-500 mt-0.5">
                    {data.ready_for_chat ? t('setup.chatReady') : t('setup.chatBlocked')}
                  </p>
                </div>
              </div>
            </div>

            {data.issues.length > 0 && (
              <ul className="space-y-2 animate-fade-up stagger-1">
                {data.issues.map((issue) => (
                  <li
                    key={issue.code}
                    className="flex items-start gap-3 rounded-xl border border-surface-200 dark:border-surface-800 bg-white/60 dark:bg-surface-900/50 px-4 py-3"
                  >
                    <StatusIcon ok={false} warn={issue.severity === 'warning'} />
                    <span className="text-sm text-surface-700 dark:text-surface-300">{issueMessage(issue)}</span>
                  </li>
                ))}
              </ul>
            )}

            <div className="grid gap-4 sm:grid-cols-2 animate-fade-up stagger-2">
              <SetupCard
                icon={Brain}
                title={t('setup.llmTitle')}
                ok={data.llm.configured}
                lines={[
                  `${t('setup.provider')}: ${data.llm.provider}`,
                  `${t('setup.model')}: ${data.llm.model}`,
                  data.llm.configured ? t('setup.keyConfigured') : t('setup.keyMissing'),
                ]}
                hint={t('setup.llmHint')}
              />
              <SetupCard
                icon={Sparkles}
                title="DeepSeek"
                ok={data.deepseek.configured}
                warn={!data.deepseek.configured}
                lines={[
                  data.deepseek.configured ? t('setup.keyConfigured') : t('setup.keyOptional'),
                  data.deepseek.usage_hint,
                ]}
                hint={t('setup.deepseekHint')}
              />
              <SetupCard
                icon={Server}
                title={t('setup.infraTitle')}
                ok={data.readiness.status === 'ok'}
                lines={Object.entries(data.readiness.checks).map(
                  ([name, check]) => `${name}: ${check.status}`,
                )}
              />
              <SetupCard
                icon={ImageIcon}
                title={t('setup.ocrTitle')}
                ok={!data.ocr.enabled || !data.issues.some((i) => i.code.startsWith('ocr'))}
                warn={data.ocr.enabled && data.issues.some((i) => i.code.startsWith('ocr'))}
                lines={[
                  `${t('setup.ocrEnabled')}: ${data.ocr.enabled ? '✓' : '—'}`,
                  `${t('setup.ocrLang')}: ${data.ocr.languages}`,
                  `${t('setup.embedding')}: ${data.embedding.provider}`,
                ]}
              />
            </div>

            <div className="setup-env-guide rounded-2xl border border-surface-200 dark:border-surface-800 bg-surface-50/80 dark:bg-surface-900/40 p-5 animate-fade-up stagger-3">
              <p className="font-display text-lg font-semibold text-surface-900 dark:text-surface-100 mb-3">
                {t('setup.envGuideTitle')}
              </p>
              <pre className="text-xs font-mono text-surface-600 dark:text-surface-400 overflow-x-auto leading-relaxed bg-surface-100/80 dark:bg-surface-950/60 rounded-xl p-4 border border-surface-200 dark:border-surface-800">
{`# 通义千问（默认问答）
LLM_PROVIDER=qwen
LLM_API_KEY=<your-dashscope-key>

# DeepSeek（向量或备用 LLM）
DEEPSEEK_API_KEY=<your-deepseek-key>

# 改后端后重建
docker compose up -d --build backend celery-worker`}
              </pre>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                data-testid="setup-go-dashboard"
                onClick={() => navigate('/dashboard')}
                className="btn-primary flex items-center gap-2"
              >
                {t('setup.goDashboard')}
                <ArrowRight className="w-4 h-4" />
              </button>
              {data.overall_ok && (
                <button
                  type="button"
                  onClick={() => navigate('/dashboard')}
                  className="btn-secondary"
                >
                  {t('setup.createKb')}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function SetupCard({
  icon: Icon,
  title,
  ok,
  warn,
  lines,
  hint,
}: {
  icon: ComponentType<{ className?: string }>;
  title: string;
  ok: boolean;
  warn?: boolean;
  lines: string[];
  hint?: string;
}) {
  return (
    <div className="setup-card rounded-2xl border border-surface-200 dark:border-surface-800 bg-white/70 dark:bg-surface-900/60 p-4 transition-all duration-300 hover:border-brand-500/25 hover:shadow-glow">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-9 h-9 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
          <Icon className="w-4 h-4 text-brand-500" />
        </span>
        <h3 className="font-semibold text-surface-900 dark:text-surface-100 flex-1">{title}</h3>
        <StatusIcon ok={ok} warn={warn} />
      </div>
      <ul className="space-y-1 text-xs text-surface-500 font-mono">
        {lines.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>
      {hint && <p className="text-xs text-surface-400 mt-3 leading-relaxed">{hint}</p>}
    </div>
  );
}
