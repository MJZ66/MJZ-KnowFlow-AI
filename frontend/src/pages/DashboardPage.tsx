import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Plus, BookOpen, ChevronLeft, ChevronRight, Lock, Globe, Loader2 } from 'lucide-react';
import { useUserStore } from '../stores/userStore';
import UserNavActions from '../components/UserNavActions';
import { useKBStore } from '../stores/kbStore';
import KnowledgeBaseCard from '../components/KnowledgeBaseCard';
import AppShell from '../components/AppShell';
import TabPanel from '../components/TabPanel';

const PAGE_SIZE_OPTIONS = [6, 12, 24];

export default function DashboardPage() {
  const { t } = useTranslation();
  const user = useUserStore((s) => s.user);
  const { kbs, kbTotal, isLoading, fetchKBs, fetchPublicKBs, publicKbs, publicKbTotal, createKB } = useKBStore();
  const navigate = useNavigate();
  const [listTab, setListTab] = useState<'mine' | 'public'>('mine');
  const [publicLoading, setPublicLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(12);

  const totalPages = Math.max(1, Math.ceil(kbTotal / pageSize));

  const loadPage = useCallback(async (p: number, size: number) => {
    await fetchKBs(p * size, size);
    setPage(p);
    setPageSize(size);
  }, [fetchKBs]);

  useEffect(() => {
    if (listTab === 'mine') {
      loadPage(0, pageSize);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchKBs, listTab]);

  useEffect(() => {
    if (listTab !== 'public') return;
    setPublicLoading(true);
    fetchPublicKBs(0, 50).finally(() => setPublicLoading(false));
  }, [listTab, fetchPublicKBs]);

  const handleCreate = async () => {
    if (!newName.trim() || creating) return;
    setCreating(true);
    try {
      const kb = await createKB(newName.trim(), newDesc.trim(), 'private');
      setShowCreate(false);
      setNewName('');
      setNewDesc('');
      navigate(`/kbs/${kb.id}`);
    } finally {
      setCreating(false);
    }
  };

  const rangeStart = kbTotal === 0 ? 0 : page * pageSize + 1;
  const rangeEnd = Math.min((page + 1) * pageSize, kbTotal);

  return (
    <AppShell
      userLabel={user?.username}
      actions={<UserNavActions />}
    >
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-10 animate-fade-up">
        <div>
          <p className="section-label mb-2">{t('kb.myList')}</p>
          <h2 className="font-display text-3xl font-semibold text-surface-900 dark:text-surface-100">{t('kb.myList')}</h2>
          <p className="text-surface-500 mt-2 max-w-lg">
            {listTab === 'mine' ? t('kb.privateSubtitle') : t('kb.publicSubtitle')}
          </p>
        </div>
        {listTab === 'mine' && (
          <button
            type="button"
            data-testid="kb-create-open"
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2 shrink-0 self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            {t('kb.create')}
          </button>
        )}
      </div>

      <div className="admin-tabs mb-8">
        <button
          type="button"
          data-testid="dashboard-tab-mine"
          onClick={() => setListTab('mine')}
          className={listTab === 'mine' ? 'admin-tab-active' : 'admin-tab'}
        >
          <Lock className="w-4 h-4" />
          {t('kb.tabPrivate')}
        </button>
        <button
          type="button"
          data-testid="dashboard-tab-public"
          onClick={() => setListTab('public')}
          className={listTab === 'public' ? 'admin-tab-active' : 'admin-tab'}
        >
          <Globe className="w-4 h-4" />
          {t('kb.tabPublic')}
        </button>
      </div>

      {showCreate && (
        <div
          className="modal-backdrop fixed inset-0 z-30 flex items-center justify-center bg-black/60 backdrop-blur-md p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setShowCreate(false)}
        >
          <div
            className="modal-panel card w-full max-w-md space-y-4 shadow-glow border-brand-600/20"
            data-testid="kb-create-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-display text-xl font-semibold text-surface-100">{t('kb.create')}</h3>
            <input
              data-testid="kb-create-name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="input-field"
              placeholder={t('kb.name')}
              autoFocus
            />
            <textarea
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              className="input-field resize-none"
              rows={3}
              placeholder={t('kb.descriptionPlaceholder')}
            />
            <div className="flex gap-3 justify-end pt-1">
              <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">
                {t('common.cancel')}
              </button>
              <button
                type="button"
                data-testid="kb-create-submit"
                onClick={() => void handleCreate()}
                className={`btn-primary inline-flex items-center gap-2 transition-all ${
                  creating ? 'opacity-80 cursor-wait' : 'active:scale-[0.98]'
                }`}
                disabled={!newName.trim() || creating}
              >
                {creating && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('common.confirm')}
              </button>
            </div>
          </div>
        </div>
      )}

      <TabPanel panelKey={listTab}>
      {listTab === 'public' ? (
        publicLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card animate-pulse h-32" />
            ))}
          </div>
        ) : publicKbs.length === 0 ? (
          <div className="card p-12 text-center text-surface-500 text-sm">{t('kb.publicEmpty')}</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {publicKbs.map((kb) => (
              <KnowledgeBaseCard key={kb.id} kb={kb} showOwner onClick={() => navigate(`/kbs/${kb.id}`)} />
            ))}
          </div>
        )
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="w-10 h-10 rounded-lg bg-surface-800 mb-3" />
              <div className="h-5 bg-surface-800 rounded w-3/4 mb-2" />
              <div className="h-4 bg-surface-800 rounded w-full" />
            </div>
          ))}
        </div>
      ) : kbs.length === 0 && kbTotal === 0 ? (
        <div className="text-center py-24 card max-w-lg mx-auto border-dashed border-surface-700">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-5">
            <BookOpen className="w-8 h-8 text-brand-400" />
          </div>
            <h3 className="font-display text-xl font-semibold text-surface-800 dark:text-surface-200 mb-2">{t('kb.empty')}</h3>
          <p className="text-surface-500 mb-8 text-sm leading-relaxed">{t('kb.emptyHint')}</p>
          <button type="button" onClick={() => setShowCreate(true)} className="btn-primary">
            {t('kb.createFirst')}
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {kbs.map((kb, idx) => (
              <div key={kb.id} className={`animate-fade-up stagger-${Math.min(idx + 1, 3)}`}>
                <KnowledgeBaseCard kb={kb} onClick={() => navigate(`/kbs/${kb.id}`)} />
              </div>
            ))}
          </div>

          {listTab === 'mine' && kbTotal > 0 && (
            <div
              className="flex flex-wrap items-center justify-between gap-4 mt-10 pt-6 border-t border-surface-800/80"
              data-testid="kb-pagination"
            >
              <p className="text-sm text-surface-500">
                {t('pagination.range', { start: rangeStart, end: rangeEnd, total: kbTotal })}
              </p>
              <div className="flex items-center gap-3">
                <label className="text-xs text-surface-500 flex items-center gap-2">
                  {t('pagination.pageSize')}
                  <select
                    data-testid="kb-page-size"
                    className="input-field py-1 px-2 text-sm w-auto"
                    value={pageSize}
                    onChange={(e) => {
                      const size = Number(e.target.value);
                      loadPage(0, size);
                    }}
                  >
                    {PAGE_SIZE_OPTIONS.map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  data-testid="kb-page-prev"
                  className="btn-ghost p-2 disabled:opacity-40"
                  disabled={page === 0}
                  onClick={() => loadPage(page - 1, pageSize)}
                  aria-label={t('pagination.prev')}
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-surface-400 tabular-nums min-w-[4.5rem] text-center">
                  {t('pagination.pageOf', { current: page + 1, total: totalPages })}
                </span>
                <button
                  type="button"
                  data-testid="kb-page-next"
                  className="btn-ghost p-2 disabled:opacity-40"
                  disabled={(page + 1) * pageSize >= kbTotal}
                  onClick={() => loadPage(page + 1, pageSize)}
                  aria-label={t('pagination.next')}
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
      </TabPanel>
    </AppShell>
  );
}
