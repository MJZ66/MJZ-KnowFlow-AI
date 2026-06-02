import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Users, Shield, Activity } from 'lucide-react';
import { api } from '../api/client';
import { useUserStore } from '../stores/userStore';

interface SystemStatus {
  users: number;
  knowledge_bases: number;
  documents: number;
  chat_sessions: number;
  active_tasks: number;
}

export default function AdminPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useUserStore((s) => s.user);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [users, setUsers] = useState<unknown[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'users'>('overview');

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';

  useEffect(() => {
    if (!isAdmin) return;
    api<SystemStatus>('/api/admin/system/status').then(setStatus).catch(() => {});
  }, [isAdmin]);

  useEffect(() => {
    if (!isAdmin || activeTab !== 'users') return;
    api<unknown[]>('/api/admin/users').then(setUsers).catch(() => {});
  }, [isAdmin, activeTab]);

  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-950">
        <div className="text-center">
          <Shield className="w-16 h-16 mx-auto text-surface-700 mb-4" />
          <h2 className="text-xl font-semibold text-surface-300 mb-2">{t('common.noPermission')}</h2>
          <p className="text-surface-500 mb-4">{t('common.needAdmin')}</p>
          <button onClick={() => navigate('/dashboard')} className="btn-primary">{t('common.returnHome')}</button>
        </div>
      </div>
    );
  }

  const tabs = [
    { key: 'overview' as const, label: t('admin.overview'), icon: Activity },
    { key: 'users' as const, label: t('admin.users'), icon: Users },
  ];

  return (
    <div className="min-h-screen bg-surface-950">
      <header className="border-b border-surface-800 bg-surface-950/80 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center gap-4">
          <button onClick={() => navigate('/dashboard')} className="btn-ghost p-1.5" title={t('common.back')}>
            <ArrowLeft className="w-4 h-4" />
          </button>
          <Shield className="w-5 h-5 text-brand-400" />
          <h1 className="text-lg font-bold text-surface-100">{t('admin.title')}</h1>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex gap-1 mb-8 bg-surface-900 rounded-lg p-1 w-fit">
          {tabs.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                activeTab === tab.key ? 'bg-surface-700 text-surface-100' : 'text-surface-400 hover:text-surface-200'
              }`}>
              <tab.icon className="w-4 h-4" />{tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'overview' && status && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: t('admin.userCount'), value: status.users },
              { label: t('admin.kbCount'), value: status.knowledge_bases },
              { label: t('admin.docCount'), value: status.documents },
              { label: t('admin.sessionCount'), value: status.chat_sessions },
              { label: t('admin.activeTasks'), value: status.active_tasks },
            ].map((stat) => (
              <div key={stat.label} className="card text-center">
                <div className="text-3xl font-bold text-brand-400 mb-1">{stat.value}</div>
                <div className="text-sm text-surface-400">{stat.label}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'users' && (
          <div className="card overflow-hidden !p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-800">
                  <th className="text-left py-3 px-4 text-surface-400 font-medium">ID</th>
                  <th className="text-left py-3 px-4 text-surface-400 font-medium">{t('auth.username')}</th>
                  <th className="text-left py-3 px-4 text-surface-400 font-medium">{t('auth.email')}</th>
                  <th className="text-left py-3 px-4 text-surface-400 font-medium">Role</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u: any) => (
                  <tr key={u.id} className="border-b border-surface-800/50 hover:bg-surface-800/30">
                    <td className="py-3 px-4 text-surface-300">{u.id}</td>
                    <td className="py-3 px-4 text-surface-200">{u.username}</td>
                    <td className="py-3 px-4 text-surface-400">{u.email}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        u.role === 'super_admin' ? 'bg-purple-500/10 text-purple-400' :
                        u.role === 'admin' ? 'bg-brand-500/10 text-brand-400' :
                        'bg-surface-700 text-surface-300'
                      }`}>{u.role}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
