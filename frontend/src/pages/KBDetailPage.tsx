import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Trash2, MessageSquare, FileText, BookOpen, Search,
  User, Bot, PanelRightClose, PanelRightOpen, Loader2, Hash, List, Eye,
} from 'lucide-react';
import AppPageHeader from '../components/AppPageHeader';
import IconActionButton from '../components/IconActionButton';
import MobileSheet from '../components/MobileSheet';
import KBMembersPanel from '../components/KBMembersPanel';
import { useKBStore } from '../stores/kbStore';
import { useUserStore } from '../stores/userStore';
import { useChatStore } from '../stores/chatStore';
import FileUploader from '../components/FileUploader';
import DocumentStatusBadge from '../components/DocumentStatusBadge';
import SessionList from '../components/SessionList';
import ChatInput from '../components/ChatInput';
import ReferencePanel from '../components/ReferencePanel';
import DocumentPreviewPanel from '../components/DocumentPreviewPanel';
import MarkdownRenderer from '../components/MarkdownRenderer';
import KBPublishPanel from '../components/KBPublishPanel';
import { api } from '../api/client';
import { parseApiError } from '../utils/error';
import { confirmAction } from '../stores/confirmStore';
import { toast } from '../stores/toastStore';
import type { Document as DocType, ChatSession, ChatMessage, SSEReference, DocumentStatus } from '../types';
import { relativeTime } from '../utils/date';

const DOC_PAGE_SIZE = 20;
const DOC_STATUSES: Array<DocumentStatus | ''> = ['', 'completed', 'failed', 'uploaded', 'parsing', 'chunking', 'embedding'];

export default function KBDetailPage() {
  const { t } = useTranslation();
  const { kbId } = useParams<{ kbId: string }>();
  const kbIdNum = Number(kbId);
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const user = useUserStore((s) => s.user);

  const { currentKB, fetchKB, deleteKB } = useKBStore();
  const [documents, setDocuments] = useState<DocType[]>([]);
  const [docLoading, setDocLoading] = useState(true);
  const [docSearch, setDocSearch] = useState('');
  const [docStatusFilter, setDocStatusFilter] = useState<DocumentStatus | ''>('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewDocId, setPreviewDocId] = useState<number | null>(null);
  const [previewChunkId, setPreviewChunkId] = useState<number | null>(null);
  const [previewChunkIndex, setPreviewChunkIndex] = useState<number | null>(null);

  const [deletingKb, setDeletingKb] = useState(false);
  const [deletingDocId, setDeletingDocId] = useState<number | null>(null);
  const [creatingSession, setCreatingSession] = useState(false);
  const [deletingSessionId, setDeletingSessionId] = useState<number | null>(null);
  const [navigatingBack, setNavigatingBack] = useState(false);
  const [docPage, setDocPage] = useState(0);
  const [docTotal, setDocTotal] = useState(0);

  const [mobilePane, setMobilePane] = useState<'docs' | 'chat'>('chat');
  const [sessionSheetOpen, setSessionSheetOpen] = useState(false);
  const [refsSheetOpen, setRefsSheetOpen] = useState(false);
  const [showRefs, setShowRefs] = useState(true);

  const {
    sessions, currentSession, messages, isStreaming,
    streamContent, references, streamError, retrievalStatus, retrievalStats,
    fetchSessions, createSession, deleteSession,
    setCurrentSession, fetchMessages, sendMessage, stopStreaming,
  } = useChatStore();

  const isOwner = user?.id === currentKB?.user_id;

  const handleReferenceClick = (ref: SSEReference) => {
    if (!ref.document_id) return;
    setPreviewDocId(ref.document_id);
    setPreviewChunkId(ref.chunk_id ?? null);
    setPreviewChunkIndex(ref.chunk_index ?? null);
    setPreviewOpen(true);
    setRefsSheetOpen(false);
  };

  const loadDocs = useCallback(async (
    page = 0,
    search = docSearch,
    status = docStatusFilter,
    options?: { silent?: boolean },
  ) => {
    if (!options?.silent) setDocLoading(true);
    try {
      const skip = page * DOC_PAGE_SIZE;
      const params = new URLSearchParams({
        skip: String(skip),
        limit: String(DOC_PAGE_SIZE),
      });
      if (search.trim()) params.set('q', search.trim());
      if (status) params.set('status', status);

      const data = await api<{ items: DocType[]; total: number }>(
        `/api/kbs/${kbIdNum}/documents?${params.toString()}`,
      );
      setDocuments(data.items);
      setDocTotal(data.total);
      setDocPage(page);
    } catch (err: unknown) {
      toast(parseApiError(err), 'error');
    } finally {
      setDocLoading(false);
    }
  }, [kbIdNum, docSearch, docStatusFilter]);

  useEffect(() => {
    if (kbIdNum) {
      fetchKB(kbIdNum);
      loadDocs(0);
      fetchSessions(kbIdNum);
    }
  }, [kbIdNum, fetchKB, fetchSessions]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (kbIdNum) void loadDocs(0);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [docSearch, docStatusFilter, kbIdNum, loadDocs]);

  useEffect(() => {
    const hasProcessing = documents.some((d) => !['completed', 'failed'].includes(d.status));
    if (!hasProcessing) return;
    const interval = setInterval(
      () => void loadDocs(docPage, docSearch, docStatusFilter, { silent: true }),
      3000,
    );
    return () => clearInterval(interval);
  }, [documents, loadDocs, docPage]);

  useEffect(() => {
    if (currentSession) fetchMessages(currentSession.id);
  }, [currentSession, fetchMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

  const handleUploaded = (doc: DocType) => {
    setDocuments((prev) => [doc, ...prev.filter((d) => d.id !== doc.id)]);
    setDocTotal((n) => n + 1);
    toast(t('document.uploadSuccess'), 'success');
  };

  const handleOpenPreview = (docId: number) => {
    setPreviewDocId(docId);
    setPreviewChunkId(null);
    setPreviewChunkIndex(null);
    setPreviewOpen(true);
  };

  const handleDeleteDoc = async (docId: number) => {
    if (deletingDocId !== null) return;
    const ok = await confirmAction({
      title: t('document.delete'),
      message: t('document.confirmDelete'),
      confirmLabel: t('common.delete'),
      variant: 'danger',
    });
    if (!ok) return;
    setDeletingDocId(docId);
    try {
      await api(`/api/kbs/${kbIdNum}/documents/${docId}`, { method: 'DELETE' });
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      setDocTotal((n) => Math.max(0, n - 1));
      toast(t('document.deleted'), 'success');
    } catch (err: unknown) {
      toast(parseApiError(err), 'error');
    } finally {
      setDeletingDocId(null);
    }
  };

  const handleDeleteKB = async () => {
    if (deletingKb) return;
    const ok = await confirmAction({
      title: t('kb.settings'),
      message: t('kb.confirmDelete'),
      confirmLabel: t('common.delete'),
      variant: 'danger',
    });
    if (!ok) return;
    setDeletingKb(true);
    try {
      await deleteKB(kbIdNum);
      navigate('/dashboard', { replace: true });
    } catch (err: unknown) {
      toast(parseApiError(err), 'error');
    } finally {
      setDeletingKb(false);
    }
  };

  const handleBack = async () => {
    if (navigatingBack) return;
    setNavigatingBack(true);
    await new Promise((r) => setTimeout(r, 120));
    navigate('/dashboard');
  };

  const handleCreateSession = async () => {
    if (!kbIdNum || creatingSession) return;
    setCreatingSession(true);
    try {
      await createSession(kbIdNum);
      setMobilePane('chat');
      setSessionSheetOpen(false);
    } catch (err: unknown) {
      toast(parseApiError(err), 'error');
    } finally {
      setCreatingSession(false);
    }
  };

  const handleSelectSession = (session: ChatSession) => {
    setCurrentSession(session);
    setMobilePane('chat');
    setSessionSheetOpen(false);
  };

  const handleDeleteSession = async (session: ChatSession) => {
    if (deletingSessionId !== null) return;
    setDeletingSessionId(session.id);
    try {
      await deleteSession(session.id);
    } catch (err: unknown) {
      toast(parseApiError(err), 'error');
    } finally {
      setDeletingSessionId(null);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!currentSession) return;
    await sendMessage(currentSession.id, content);
  };

  const displayMessages: (ChatMessage & { isStreaming?: boolean })[] = [...messages];
  if (isStreaming && streamContent) {
    displayMessages.push({
      id: -1, session_id: currentSession?.id || 0, user_id: 0,
      role: 'assistant', content: streamContent,
      created_at: new Date().toISOString(), isStreaming: true,
    });
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const sessionListProps = {
    sessions,
    currentSessionId: currentSession?.id || null,
    onSelect: handleSelectSession,
    onCreate: handleCreateSession,
    onDelete: handleDeleteSession,
    creating: creatingSession,
    deletingId: deletingSessionId,
  };

  const chatMessages = (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      {!currentSession ? (
        <div className="flex flex-col items-center justify-center h-full text-center px-4">
          <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-4">
            <MessageSquare className="w-7 h-7 text-brand-400" />
          </div>
          <p className="text-surface-400 text-sm max-w-xs leading-relaxed">{t('chat.startHint')}</p>
          <button
            type="button"
            data-testid="chat-new-session"
            onClick={() => void handleCreateSession()}
            disabled={creatingSession}
            className={`btn-primary mt-6 text-sm inline-flex items-center gap-2 transition-all ${
              creatingSession ? 'opacity-80 cursor-wait' : 'active:scale-[0.98]'
            }`}
          >
            {creatingSession && <Loader2 className="w-4 h-4 animate-spin" />}
            {t('chat.newSession')}
          </button>
        </div>
      ) : displayMessages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-center px-4">
          <div className="w-12 h-12 rounded-xl bg-surface-800/80 flex items-center justify-center mb-3">
            <Bot className="w-6 h-6 text-brand-400" />
          </div>
          <p className="text-surface-500 text-sm">{t('chat.inputHint')}</p>
        </div>
      ) : (
        <div className="max-w-3xl mx-auto space-y-4">
          {retrievalStatus && (
            <div className="flex items-center gap-2 text-sm text-brand-400 bg-brand-500/5 border border-brand-500/20 rounded-lg px-4 py-2">
              <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
              {retrievalStatus}
            </div>
          )}
          {retrievalStats && (retrievalStats.mode || retrievalStats.raw_count != null) && (
            <div className="text-xs text-surface-500 bg-surface-900/80 border border-surface-800 rounded-lg px-4 py-2 font-mono">
              {t('chat.retrievalStats', {
                mode: retrievalStats.mode ?? 'vector',
                raw: retrievalStats.raw_count ?? '-',
                valid: retrievalStats.valid_count ?? '-',
                reranked: retrievalStats.reranked_count ?? retrievalStats.count ?? '-',
              })}
              {retrievalStats.cached && <span className="ml-2 text-brand-400">(cache)</span>}
            </div>
          )}
          {displayMessages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                msg.role === 'user'
                  ? 'bg-surface-700/90 border border-surface-600'
                  : 'bg-brand-500/15 border border-brand-500/25'
              }`}>
                {msg.role === 'user'
                  ? <User className="w-4 h-4 text-surface-300" />
                  : <Bot className="w-4 h-4 text-brand-400" />}
              </div>
              <div className={`flex-1 min-w-0 text-sm max-w-[85%] ${
                msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'
              }`}>
                {msg.role === 'assistant' ? (
                  <MarkdownRenderer content={msg.content} />
                ) : (
                  <div className="text-surface-100 leading-relaxed whitespace-pre-wrap break-words">{msg.content}</div>
                )}
                {msg.isStreaming && (
                  <span className="inline-block w-2 h-4 bg-brand-400 animate-shimmer rounded-sm align-text-bottom ml-0.5" />
                )}
              </div>
            </div>
          ))}
          {streamError && (
            <div className="text-red-400 text-sm bg-red-500/5 border border-red-500/20 rounded-lg p-3">
              {parseApiError(new Error(streamError))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}
    </div>
  );

  return (
    <div className="h-screen flex flex-col page-bg overflow-hidden">
      <AppPageHeader
        title={currentKB?.name || t('common.loading')}
        subtitle={currentKB?.description || undefined}
        icon={<BookOpen className="w-4 h-4 text-brand-600 dark:text-brand-400" />}
        onBack={() => void handleBack()}
        backPending={navigatingBack}
        themeTestId="kb-detail-theme-switcher"
        langTestId="kb-detail-lang-switcher"
        actions={
          isOwner ? (
            <IconActionButton
              testId="kb-delete"
              onClick={() => void handleDeleteKB()}
              pending={deletingKb}
              variant="danger"
              title={t('common.delete')}
              icon={<Trash2 className="w-4 h-4" />}
            />
          ) : undefined
        }
      />

      <div className="lg:hidden shrink-0 px-3 py-2 border-b border-surface-200 dark:border-surface-800 bg-surface-50/80 dark:bg-surface-950/40">
        <div className="flex gap-2">
          <button
            type="button"
            data-testid="mobile-pane-docs"
            onClick={() => setMobilePane('docs')}
            className={mobilePane === 'docs' ? 'admin-tab-active flex-1 text-sm py-2' : 'admin-tab flex-1 text-sm py-2'}
          >
            <FileText className="w-4 h-4 inline mr-1.5" />
            {t('document.list')}
          </button>
          <button
            type="button"
            data-testid="mobile-pane-chat"
            onClick={() => setMobilePane('chat')}
            className={mobilePane === 'chat' ? 'admin-tab-active flex-1 text-sm py-2' : 'admin-tab flex-1 text-sm py-2'}
          >
            <MessageSquare className="w-4 h-4 inline mr-1.5" />
            {t('chat.startChat')}
          </button>
        </div>
        {mobilePane === 'chat' && (
          <div className="flex gap-2 mt-2">
            <button
              type="button"
              data-testid="mobile-sessions-open"
              onClick={() => setSessionSheetOpen(true)}
              className="btn-secondary flex-1 text-xs py-2 inline-flex items-center justify-center gap-1.5"
            >
              <List className="w-3.5 h-3.5" />
              {t('chat.sessions')}
            </button>
            <button
              type="button"
              data-testid="mobile-refs-open"
              onClick={() => setRefsSheetOpen(true)}
              className="btn-secondary flex-1 text-xs py-2 inline-flex items-center justify-center gap-1.5"
            >
              <Hash className="w-3.5 h-3.5" />
              {t('chat.references')} ({references.length})
            </button>
          </div>
        )}
      </div>

      {currentKB && <KBPublishPanel kb={currentKB} />}
      {currentKB && <KBMembersPanel kb={currentKB} />}

      <div className="flex-1 flex overflow-hidden min-h-0">
        <div className={`w-full lg:w-[35%] lg:min-w-[320px] border-r border-surface-200/90 dark:border-surface-800/90 flex flex-col overflow-hidden bg-white/50 dark:bg-surface-950/40 ${
          mobilePane === 'docs' ? 'flex' : 'hidden lg:flex'
        }`}>
          <div className="p-4 border-b border-surface-800/80">
            <p className="section-label mb-3">{t('document.upload')}</p>
            <FileUploader kbId={kbIdNum} onUploaded={handleUploaded} />
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <p className="pane-header mb-3">
              <FileText className="w-4 h-4 text-brand-400" />
              {t('document.list')}
              <span className="text-surface-600 font-normal tabular-nums">({docTotal})</span>
            </p>

            <div className="flex flex-col gap-2 mb-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500" />
                <input
                  type="search"
                  data-testid="doc-search"
                  value={docSearch}
                  onChange={(e) => setDocSearch(e.target.value)}
                  className="input-field pl-9 text-sm"
                  placeholder={t('document.searchPlaceholder')}
                />
              </div>
              <select
                data-testid="doc-status-filter"
                value={docStatusFilter}
                onChange={(e) => setDocStatusFilter(e.target.value as DocumentStatus | '')}
                className="input-field text-sm"
              >
                <option value="">{t('document.filterAll')}</option>
                {DOC_STATUSES.filter(Boolean).map((st) => (
                  <option key={st} value={st}>{t(`document.status.${st}`)}</option>
                ))}
              </select>
            </div>

            {docLoading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (<div key={i} className="bg-surface-900 rounded-lg h-14 animate-pulse" />))}
              </div>
            ) : documents.length === 0 ? (
              <p className="text-surface-500 text-sm text-center py-8">{t('document.empty')}</p>
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div key={doc.id} className="doc-row">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-surface-200 text-sm font-medium truncate">{doc.original_filename}</p>
                        <p className="text-surface-600 text-xs mt-0.5">
                          {formatSize(doc.file_size)} · {relativeTime(doc.created_at)}
                        </p>
                      </div>
                      <div className="flex items-center gap-0.5 shrink-0">
                        <button
                          type="button"
                          data-testid={`doc-preview-${doc.id}`}
                          onClick={() => handleOpenPreview(doc.id)}
                          className="p-1 text-surface-600 hover:text-brand-400 active:scale-90 transition-all"
                          title={t('document.preview')}
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDeleteDoc(doc.id)}
                          disabled={deletingDocId === doc.id}
                          className={`p-1 transition-all ${
                            deletingDocId === doc.id
                              ? 'text-red-400/70 cursor-wait'
                              : 'text-surface-600 hover:text-red-400 active:scale-90'
                          }`}
                          title={t('common.delete')}
                        >
                          {deletingDocId === doc.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <DocumentStatusBadge status={doc.status} />
                      {doc.error_message && (
                        <span className="text-xs text-red-400 truncate flex-1" title={doc.error_message}>
                          {doc.error_message}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {docTotal > DOC_PAGE_SIZE && (
              <div className="flex items-center justify-between mt-4 text-xs text-surface-500">
                <button type="button" className="btn-ghost px-2 py-1 disabled:opacity-40" disabled={docPage === 0} onClick={() => void loadDocs(docPage - 1)}>
                  {t('common.back')}
                </button>
                <span>{docPage + 1} / {Math.ceil(docTotal / DOC_PAGE_SIZE)}</span>
                <button type="button" className="btn-ghost px-2 py-1 disabled:opacity-40" disabled={(docPage + 1) * DOC_PAGE_SIZE >= docTotal} onClick={() => void loadDocs(docPage + 1)}>
                  →
                </button>
              </div>
            )}
          </div>
        </div>

        <div className={`flex-1 flex flex-col min-w-0 ${mobilePane === 'chat' ? 'flex' : 'hidden lg:flex'}`}>
          <div className="flex-1 flex min-h-0">
            <div className="w-56 border-r border-surface-200/90 dark:border-surface-800/90 shrink-0 hidden lg:block bg-surface-50/80 dark:bg-surface-950/30">
              <SessionList {...sessionListProps} />
            </div>

            <div className="flex-1 flex flex-col min-w-0">
              {chatMessages}
              {currentSession && (
                <ChatInput onSend={handleSendMessage} onStop={stopStreaming} isStreaming={isStreaming} />
              )}
            </div>

            {showRefs && (
              <div className="w-64 border-l border-surface-200/90 dark:border-surface-800/90 shrink-0 hidden xl:block overflow-y-auto bg-surface-50/80 dark:bg-surface-950/40">
                <div className="flex items-center justify-between px-3 py-3 border-b border-surface-800/80">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-surface-500">{t('chat.references')}</h3>
                  <button type="button" onClick={() => setShowRefs(false)} className="btn-ghost p-1" title={t('chat.hideRefs')}>
                    <PanelRightClose className="w-3.5 h-3.5" />
                  </button>
                </div>
                <ReferencePanel references={references} onReferenceClick={handleReferenceClick} />
              </div>
            )}
            {!showRefs && (
              <button
                type="button"
                onClick={() => setShowRefs(true)}
                className="self-start mt-3 mr-3 btn-ghost p-1.5 shrink-0 hidden xl:block"
                title={t('chat.showRefs')}
              >
                <PanelRightOpen className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      <MobileSheet
        open={sessionSheetOpen}
        onClose={() => setSessionSheetOpen(false)}
        title={t('chat.sessions')}
        side="left"
        testId="mobile-session-sheet"
      >
        <SessionList {...sessionListProps} />
      </MobileSheet>

      <MobileSheet
        open={refsSheetOpen}
        onClose={() => setRefsSheetOpen(false)}
        title={t('chat.references')}
        side="bottom"
        testId="mobile-refs-sheet"
      >
        <ReferencePanel references={references} onReferenceClick={handleReferenceClick} />
      </MobileSheet>

      <DocumentPreviewPanel
        open={previewOpen}
        documentId={previewDocId}
        targetChunkId={previewChunkId}
        targetChunkIndex={previewChunkIndex}
        onClose={() => setPreviewOpen(false)}
      />
    </div>
  );
}
