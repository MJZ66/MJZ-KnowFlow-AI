import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Plus, BookOpen, Settings, LogOut, ChevronLeft, ChevronRight } from 'lucide-react';
import { useUserStore } from '../stores/userStore';
import { useKBStore } from '../stores/kbStore';
import KnowledgeBaseCard from '../components/KnowledgeBaseCard';
import LangSwitcher from '../components/LangSwitcher';

const PAGE_SIZE_OPTIONS = [6, 12, 24];

export default function DashboardPage() {
  const { t } = useTranslation();
  const user = useUserStore((s) => s.user);
  const logout = useUserStore((s) => s.logout);
  const { kbs, kbTotal, isLoading, fetchKBs, createKB } = useKBStore();
  const navigate = useNavigate();
  const [showCreate, setShowCreate] = useState(false);
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
    loadPage(0, pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchKBs]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    const kb = await createKB(newName.trim(), newDesc.trim(), 'private');
    setShowCreate(false);
    setNewName('');
    setNewDesc('');
    navigate(`/kbs/${kb.id}`);
  };

  const rangeStart = kbTotal === 0 ? 0 : page * pageSize + 1;
  const rangeEnd = Math.min((page + 1) * pageSize, kbTotal);

  return (
    <div className="min-h-screen bg-surface-950">
      <header className="border-b border-surface-800 bg-surface-950/80 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-500/10 flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-brand-400" />
            </div>
            <h1 className="text-lg font-bold text-surface-100">{t('app.name')}</h1>
          </div>
          <div className="flex items-center gap-2">
            <LangSwitcher />
            <span className="text-sm text-surface-400">{user?.username}</span>
            {user?.role !== 'user' && (
              <button onClick={() => navigate('/admin')} className="btn-ghost p-2" title={t('admin.title')}>
                <Settings className="w-4 h-4" />
              </button>
            )}
            <button onClick={logout} className="btn-ghost p-2 text-red-400" title={t('auth.logout')}>
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-surface-100">{t('kb.myList')}</h2>
            <p className="text-surface-500 mt-1">{t('kb.listSubtitle')}</p>
          </div>
          <button
            type="button"
            data-testid="kb-create-open"
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            {t('kb.create')}
          </button>
        </div>

        {showCreate && (
          <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="card w-full max-w-md space-y-4" data-testid="kb-create-modal">
              <h3 className="text-lg font-semibold text-surface-100">{t('kb.create')}</h3>
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
              <div className="flex gap-3 justify-end">
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">
                  {t('common.cancel')}
                </button>
                <button
                  type="button"
                  data-testid="kb-create-submit"
                  onClick={handleCreate}
                  className="btn-primary"
                  disabled={!newName.trim()}
                >
                  {t('common.confirm')}
                </button>
              </div>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card animate-pulse">
                <div className="w-10 h-10 rounded-lg bg-surface-800 mb-3" />
                <div className="h-5 bg-surface-800 rounded w-3/4 mb-2" />
                <div className="h-4 bg-surface-800 rounded w-full" />
              </div>
            ))}
          </div>
        ) : kbs.length === 0 && kbTotal === 0 ? (
          <div className="text-center py-20">
            <BookOpen className="w-16 h-16 mx-auto text-surface-700 mb-4" />
            <h3 className="text-xl font-semibold text-surface-300 mb-2">{t('kb.empty')}</h3>
            <p className="text-surface-500 mb-6">{t('kb.emptyHint')}</p>
            <button type="button" onClick={() => setShowCreate(true)} className="btn-primary">
              {t('kb.createFirst')}
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {kbs.map((kb) => (
                <KnowledgeBaseCard key={kb.id} kb={kb} onClick={() => navigate(`/kbs/${kb.id}`)} />
              ))}
            </div>

            {kbTotal > 0 && (
              <div
                className="flex flex-wrap items-center justify-between gap-4 mt-8 pt-4 border-t border-surface-800"
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
                  <span className="text-sm text-surface-400 tabular-nums">
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
      </main>
    </div>
  );
}
