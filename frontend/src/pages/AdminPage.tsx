import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Users, Shield, Activity, BookOpen, FileText, MessageSquare, Cpu,
  Radio, TrendingUp, Globe,
} from 'lucide-react';
import AdminPublishApprovals from '../components/admin/AdminPublishApprovals';
import { api } from '../api/client';
import { useUserStore } from '../stores/userStore';
import { parseApiError } from '../utils/error';
import AdminShell from '../components/AdminShell';
import TabPanel from '../components/TabPanel';
import ThemeSwitcher from '../components/ThemeSwitcher';
import AdminActivityChart, { type DailyActivePoint } from '../components/admin/AdminActivityChart';
import AdminUsersTable, { type AdminUserRow } from '../components/admin/AdminUsersTable';

interface SystemStatus {
  users: number;
  knowledge_bases: number;
  documents: number;
  chat_sessions: number;
  active_tasks: number;
  online_count: number;
  dau_today: number;
  test_users?: number;
}

interface AdminUserListResponse {
  items: AdminUserRow[];
  total: number;
  online_count: number;
  test_account_count?: number;
}

interface AdminAnalytics {
  total_users: number;
  online_count: number;
  dau_today: number;
  daily_active: DailyActivePoint[];
  online_threshold_minutes: number;
}

const STAT_ICONS = [Users, Radio, TrendingUp, BookOpen, FileText] as const;

export default function AdminPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useUserStore((s) => s.user);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [onlineCount, setOnlineCount] = useState(0);
  const [usersLoading, setUsersLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'publish'>('overview');
  const [excludeTest, setExcludeTest] = useState(true);
  const [testAccountCount, setTestAccountCount] = useState(0);
  const [actionError, setActionError] = useState('');

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';
  const isSuperAdmin = user?.role === 'super_admin';

  const loadOverview = useCallback(async () => {
    setStatusLoading(true);
    try {
      const ex = excludeTest ? 'true' : 'false';
      const [st, an] = await Promise.all([
        api<SystemStatus>(`/api/admin/system/status?exclude_test=${ex}`),
        api<AdminAnalytics>(`/api/admin/analytics?days=7&exclude_test=${ex}`),
      ]);
      setStatus(st);
      setAnalytics(an);
    } catch {
      setStatus(null);
      setAnalytics(null);
    } finally {
      setStatusLoading(false);
    }
  }, [excludeTest]);

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const ex = excludeTest ? 'true' : 'false';
      const data = await api<AdminUserListResponse>(
        `/api/admin/users?limit=100&exclude_test=${ex}`,
      );
      setUsers(data.items);
      setUserTotal(data.total);
      setOnlineCount(data.online_count);
      setTestAccountCount(data.test_account_count ?? 0);
    } catch {
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  }, [excludeTest]);

  useEffect(() => {
    if (!isAdmin) return;
    loadOverview();
  }, [isAdmin, loadOverview, excludeTest]);

  useEffect(() => {
    if (!isAdmin || activeTab !== 'users') return;
    loadUsers();
    const interval = window.setInterval(loadUsers, 30000);
    return () => window.clearInterval(interval);
  }, [isAdmin, activeTab, loadUsers, excludeTest]);

  const handleRoleChange = async (userId: number, role: string) => {
    setActionError('');
    try {
      await api(`/api/admin/users/${userId}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      });
      await loadUsers();
    } catch (err: unknown) {
      setActionError(parseApiError(err));
      await loadUsers();
    }
  };

  if (!isAdmin) {
    return (
      <div className="min-h-screen page-bg flex items-center justify-center p-6">
        <div className="card max-w-md w-full text-center animate-fade-up">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-surface-100 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 flex items-center justify-center mb-4">
            <Shield className="w-7 h-7 text-surface-400" />
          </div>
          <h2 className="font-display text-xl font-semibold text-surface-800 dark:text-surface-200 mb-2">
            {t('common.noPermission')}
          </h2>
          <p className="text-surface-500 mb-6 text-sm">{t('common.needAdmin')}</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <ThemeSwitcher />
            <button type="button" onClick={() => navigate('/dashboard')} className="btn-primary">
              {t('common.returnHome')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const tabs = [
    { key: 'overview' as const, label: t('admin.overview'), icon: Activity },
    { key: 'users' as const, label: t('admin.users'), icon: Users },
    { key: 'publish' as const, label: t('admin.publishApprovals'), icon: Globe },
  ];

  const stats = status
    ? [
        { label: t('admin.userCount'), value: status.users },
        { label: t('admin.onlineCount'), value: status.online_count },
        { label: t('admin.dauToday'), value: status.dau_today },
        { label: t('admin.kbCount'), value: status.knowledge_bases },
        { label: t('admin.docCount'), value: status.documents },
      ]
    : [];

  return (
    <AdminShell onBack={() => navigate('/dashboard')}>
      <div className="admin-hero mb-8 rounded-2xl border border-brand-500/20 bg-gradient-to-br from-brand-500/10 via-transparent to-surface-100/50 dark:to-surface-900/30 p-6 animate-fade-up">
        <p className="section-label mb-2">{t('admin.title')}</p>
        <h2 className="font-display text-2xl font-semibold text-surface-900 dark:text-surface-100">
          {t('admin.dashboardTitle')}
        </h2>
        <p className="text-surface-500 text-sm mt-2 max-w-2xl">{t('admin.dashboardSubtitle')}</p>
        <div className="flex flex-wrap items-center gap-4 mt-3">
          {analytics && (
            <p className="text-xs text-surface-500">
              {t('admin.onlineThreshold', { minutes: analytics.online_threshold_minutes })}
            </p>
          )}
          <label className="inline-flex items-center gap-2 text-xs text-surface-500 cursor-pointer select-none">
            <input
              type="checkbox"
              data-testid="admin-exclude-test-overview"
              checked={excludeTest}
              onChange={(e) => setExcludeTest(e.target.checked)}
              className="rounded border-surface-300 text-brand-600 focus:ring-brand-500/40"
            />
            {t('admin.excludeTestAccounts')}
          </label>
          {excludeTest && status && (status.test_users ?? 0) > 0 && (
            <span className="text-xs text-amber-600 dark:text-amber-400">
              {t('admin.statsExcludeHint', { count: status.test_users })}
            </span>
          )}
        </div>
      </div>

      <div className="admin-tabs mb-8">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            data-testid={`admin-tab-${tab.key}`}
            onClick={() => setActiveTab(tab.key)}
            className={activeTab === tab.key ? 'admin-tab-active' : 'admin-tab'}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <TabPanel panelKey={activeTab}>
      {activeTab === 'overview' && (
        <div className="space-y-8">
          {statusLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="admin-stat-card animate-pulse">
                  <div className="h-9 bg-surface-200 dark:bg-surface-800 rounded w-16 mx-auto mb-2" />
                  <div className="h-4 bg-surface-200 dark:bg-surface-800 rounded w-20 mx-auto" />
                </div>
              ))}
            </div>
          ) : status ? (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {stats.map((stat, idx) => {
                const Icon = STAT_ICONS[idx] ?? Activity;
                return (
                  <div key={stat.label} className="admin-stat-card animate-fade-up">
                    <div className="w-10 h-10 mx-auto rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-3">
                      <Icon className="w-5 h-5 text-brand-600 dark:text-brand-400" />
                    </div>
                    <div className="text-3xl font-bold text-brand-600 dark:text-brand-400 mb-1 tabular-nums">
                      {stat.value}
                    </div>
                    <div className="text-sm text-surface-500">{stat.label}</div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-surface-500 text-sm">{t('admin.statusUnavailable')}</p>
          )}

          {analytics && (
            <AdminActivityChart
              data={analytics.daily_active}
              highlightToday={analytics.dau_today}
            />
          )}

          {status && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="card flex items-center gap-4 !p-4">
                <MessageSquare className="w-8 h-8 text-brand-500/80" />
                <div>
                  <p className="text-2xl font-bold tabular-nums text-surface-800 dark:text-surface-100">
                    {status.chat_sessions}
                  </p>
                  <p className="text-xs text-surface-500">{t('admin.sessionCount')}</p>
                </div>
              </div>
              <div className="card flex items-center gap-4 !p-4">
                <Cpu className="w-8 h-8 text-brand-500/80" />
                <div>
                  <p className="text-2xl font-bold tabular-nums text-surface-800 dark:text-surface-100">
                    {status.active_tasks}
                  </p>
                  <p className="text-xs text-surface-500">{t('admin.activeTasks')}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'publish' && <AdminPublishApprovals />}

      {activeTab === 'users' && (
        <>
          {actionError && (
            <div className="mb-4 text-sm text-red-600 dark:text-red-400 bg-red-500/5 border border-red-500/20 rounded-lg p-3">
              {actionError}
            </div>
          )}
          {usersLoading ? (
            <div className="admin-table-wrap p-8 space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-10 bg-surface-100 dark:bg-surface-800 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : users.length === 0 ? (
            <div className="card p-12 text-center text-surface-500 text-sm">{t('admin.noUsers')}</div>
          ) : (
            <AdminUsersTable
              users={users}
              total={userTotal}
              onlineCount={onlineCount}
              testAccountCount={testAccountCount}
              excludeTest={excludeTest}
              onExcludeTestChange={setExcludeTest}
              isSuperAdmin={isSuperAdmin}
              onRoleChange={isSuperAdmin ? handleRoleChange : undefined}
            />
          )}
        </>
      )}
      </TabPanel>
    </AdminShell>
  );
}
