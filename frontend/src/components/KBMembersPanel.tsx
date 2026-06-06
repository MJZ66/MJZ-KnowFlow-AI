import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Trash2, UserPlus, Users } from 'lucide-react';
import { useKBStore } from '../stores/kbStore';
import { useUserStore } from '../stores/userStore';
import { parseApiError } from '../utils/error';
import { toast } from '../stores/toastStore';
import { confirmAction } from '../stores/confirmStore';
import type { KnowledgeBase } from '../types';

interface Props {
  kb: KnowledgeBase;
}

export default function KBMembersPanel({ kb }: Props) {
  const { t } = useTranslation();
  const user = useUserStore((s) => s.user);
  const { members, fetchMembers, addMemberByEmail, removeMember } = useKBStore();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'editor' | 'viewer'>('viewer');
  const [loading, setLoading] = useState(false);
  const [membersLoading, setMembersLoading] = useState(true);
  const [removingId, setRemovingId] = useState<number | null>(null);

  const isOwner = user?.id === kb.user_id;

  useEffect(() => {
    setMembersLoading(true);
    fetchMembers(kb.id).finally(() => setMembersLoading(false));
  }, [kb.id, fetchMembers]);

  if (!isOwner && members.length <= 1) return null;

  const handleInvite = async () => {
    const trimmed = email.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    try {
      await addMemberByEmail(kb.id, trimmed, role);
      setEmail('');
      toast(t('kb.memberAdded'), 'success');
    } catch (err: unknown) {
      toast(parseApiError(err), 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (userId: number, username: string | null) => {
    const ok = await confirmAction({
      title: t('kb.removeMemberTitle'),
      message: t('kb.removeMemberConfirm', { name: username || `#${userId}` }),
      confirmLabel: t('common.delete'),
      variant: 'danger',
    });
    if (!ok) return;
    setRemovingId(userId);
    try {
      await removeMember(kb.id, userId);
      toast(t('kb.memberRemoved'), 'success');
    } catch (err: unknown) {
      toast(parseApiError(err), 'error');
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div
      className="mx-4 mt-3 mb-1 rounded-xl border border-surface-200 dark:border-surface-800 bg-surface-50/80 dark:bg-surface-900/50 p-4"
      data-testid="kb-members-panel"
    >
      <div className="flex items-center gap-2 mb-3">
        <Users className="w-4 h-4 text-brand-600 dark:text-brand-400" />
        <p className="text-sm font-semibold text-surface-800 dark:text-surface-200">{t('kb.membersTitle')}</p>
        <span className="text-xs text-surface-500 tabular-nums">({members.length})</span>
      </div>

      {isOwner && (
        <div className="flex flex-col sm:flex-row gap-2 mb-4">
          <input
            type="email"
            data-testid="kb-member-email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input-field flex-1 text-sm"
            placeholder={t('kb.memberEmailPlaceholder')}
          />
          <select
            data-testid="kb-member-role"
            value={role}
            onChange={(e) => setRole(e.target.value as 'editor' | 'viewer')}
            className="input-field text-sm w-full sm:w-auto"
          >
            <option value="viewer">{t('kb.role.viewer')}</option>
            <option value="editor">{t('kb.role.editor')}</option>
          </select>
          <button
            type="button"
            data-testid="kb-member-invite"
            onClick={() => void handleInvite()}
            disabled={!email.trim() || loading}
            className="btn-primary text-sm inline-flex items-center justify-center gap-2 shrink-0"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
            {t('kb.inviteMember')}
          </button>
        </div>
      )}

      {membersLoading ? (
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-10 rounded-lg bg-surface-200 dark:bg-surface-800 animate-pulse" />
          ))}
        </div>
      ) : (
        <ul className="space-y-2">
          {members.map((m) => (
            <li
              key={m.id}
              className="flex items-center gap-3 rounded-lg border border-surface-200 dark:border-surface-800 bg-white/60 dark:bg-surface-950/40 px-3 py-2"
              data-testid={`kb-member-${m.user_id}`}
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-surface-800 dark:text-surface-200 truncate">
                  {m.username || m.email || `#${m.user_id}`}
                </p>
                {m.email && m.username && (
                  <p className="text-xs text-surface-500 truncate">{m.email}</p>
                )}
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400 shrink-0">
                {t(`kb.role.${m.role}`)}
              </span>
              {isOwner && m.role !== 'owner' && (
                <button
                  type="button"
                  onClick={() => void handleRemove(m.user_id, m.username ?? null)}
                  disabled={removingId === m.user_id}
                  className="p-1 text-surface-500 hover:text-red-400 shrink-0"
                  title={t('kb.removeMember')}
                >
                  {removingId === m.user_id ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
