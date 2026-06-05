import { useTranslation } from 'react-i18next';
import { Circle } from 'lucide-react';
import { format, relativeTime } from '../../utils/date';

export interface AdminUserRow {
  id: number;
  email: string;
  username: string;
  role: string;
  created_at: string;
  last_login_at: string | null;
  last_active_at: string | null;
  is_online: boolean;
  is_test_account?: boolean;
}

interface Props {
  users: AdminUserRow[];
  onlineCount: number;
  total: number;
  testAccountCount?: number;
  excludeTest: boolean;
  onExcludeTestChange: (value: boolean) => void;
  isSuperAdmin: boolean;
  onRoleChange?: (userId: number, role: string) => void;
}

export default function AdminUsersTable({
  users,
  onlineCount,
  total,
  testAccountCount = 0,
  excludeTest,
  onExcludeTestChange,
  isSuperAdmin,
  onRoleChange,
}: Props) {
  const { t } = useTranslation();

  const roleLabel = (role: string) => {
    const key = `admin.role.${role}`;
    const translated = t(key);
    return translated === key ? role : translated;
  };

  const roleClass = (role: string) => {
    if (role === 'super_admin') {
      return 'bg-violet-500/10 text-violet-700 border border-violet-500/25 dark:text-violet-400';
    }
    if (role === 'admin') {
      return 'bg-brand-500/10 text-brand-700 border border-brand-500/25 dark:text-brand-400';
    }
    return 'bg-surface-200 text-surface-600 border border-surface-300 dark:bg-surface-700 dark:text-surface-300 dark:border-transparent';
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 text-sm text-surface-500">
          <span>
            {t('admin.usersSummary', { total, online: onlineCount })}
          </span>
          {testAccountCount > 0 && (
            <span className="text-xs px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
              {t('admin.testAccountCount', { count: testAccountCount })}
            </span>
          )}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 text-xs">
            <Circle className="w-2 h-2 fill-current animate-pulse" />
            {t('admin.onlineNow')}
          </span>
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-surface-600 dark:text-surface-400 cursor-pointer select-none">
          <input
            type="checkbox"
            data-testid="admin-exclude-test"
            checked={excludeTest}
            onChange={(e) => onExcludeTestChange(e.target.checked)}
            className="rounded border-surface-300 text-brand-600 focus:ring-brand-500/40"
          />
          {t('admin.excludeTestAccounts')}
        </label>
      </div>

      <div className="admin-table-wrap" data-testid="admin-users-table">
        <table className="admin-table w-full text-sm">
          <thead>
            <tr className="border-b border-surface-200 dark:border-surface-800">
              <th>{t('admin.statusColumn')}</th>
              <th>ID</th>
              <th>{t('auth.username')}</th>
              <th>{t('auth.email')}</th>
              <th>{t('admin.roleColumn')}</th>
              <th>{t('admin.lastLogin')}</th>
              <th>{t('admin.lastActive')}</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>
                  <span
                    className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                      u.is_online
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-surface-500'
                    }`}
                    data-testid={`user-online-${u.id}`}
                  >
                    <Circle
                      className={`w-2 h-2 ${u.is_online ? 'fill-current' : 'fill-surface-400'}`}
                    />
                    {u.is_online ? t('admin.online') : t('admin.offline')}
                  </span>
                </td>
                <td className="font-mono text-surface-500">{u.id}</td>
                <td className="font-medium text-surface-800 dark:text-surface-200">
                  <span className="inline-flex items-center gap-2 flex-wrap">
                    {u.username}
                    {u.is_test_account && (
                      <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/25 font-semibold">
                        {t('admin.testAccountBadge')}
                      </span>
                    )}
                  </span>
                </td>
                <td className="text-surface-500 max-w-[200px] truncate">{u.email}</td>
                <td>
                  {isSuperAdmin && onRoleChange ? (
                    <select
                      className="input-field py-1 px-2 text-xs w-auto"
                      value={u.role}
                      onChange={(e) => onRoleChange(u.id, e.target.value)}
                      aria-label={t('admin.roleColumn')}
                    >
                      <option value="user">{roleLabel('user')}</option>
                      <option value="admin">{roleLabel('admin')}</option>
                      <option value="super_admin">{roleLabel('super_admin')}</option>
                    </select>
                  ) : (
                    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${roleClass(u.role)}`}>
                      {roleLabel(u.role)}
                    </span>
                  )}
                </td>
                <td className="text-surface-500 text-xs whitespace-nowrap">
                  {u.last_login_at ? format(u.last_login_at) : '—'}
                </td>
                <td className="text-surface-500 text-xs whitespace-nowrap">
                  {u.last_active_at ? relativeTime(u.last_active_at) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
