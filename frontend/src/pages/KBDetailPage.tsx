import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeft, Trash2, MessageSquare, FileText, BookOpen,
  User, Bot, PanelRightClose, PanelRightOpen,
} from 'lucide-react';
import { useKBStore } from '../stores/kbStore';
import { useChatStore } from '../stores/chatStore';
import FileUploader from '../components/FileUploader';
import DocumentStatusBadge from '../components/DocumentStatusBadge';
import SessionList from '../components/SessionList';
import ChatInput from '../components/ChatInput';
import ReferencePanel from '../components/ReferencePanel';
import DocumentPreviewPanel from '../components/DocumentPreviewPanel';
import MarkdownRenderer from '../components/MarkdownRenderer';
import LangSwitcher from '../components/LangSwitcher';
import ThemeSwitcher from '../components/ThemeSwitcher';
import KBPublishPanel from '../components/KBPublishPanel';
import { api } from '../api/client';
import { parseApiError } from '../utils/error';
import type { Document as DocType, ChatSession, ChatMessage, SSEReference } from '../types';
import { relativeTime } from '../utils/date';

export default function KBDetailPage() {
  const { t } = useTranslation();
  const { kbId } = useParams<{ kbId: string }>();
  const kbIdNum = Number(kbId);
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Document state
  const { currentKB, fetchKB, deleteKB } = useKBStore();
  const [documents, setDocuments] = useState<DocType[]>([]);
  const [docLoading, setDocLoading] = useState(true);
  const [uploadError, setUploadError] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewDocId, setPreviewDocId] = useState<number | null>(null);
  const [previewChunkId, setPreviewChunkId] = useState<number | null>(null);
  const [previewChunkIndex, setPreviewChunkIndex] = useState<number | null>(null);

  const handleReferenceClick = (ref: SSEReference) => {
    if (!ref.document_id) return;
    setPreviewDocId(ref.document_id);
    setPreviewChunkId(ref.chunk_id ?? null);
    setPreviewChunkIndex(ref.chunk_index ?? null);
    setPreviewOpen(true);
  };

  const [docPage, setDocPage] = useState(0);
  const DOC_PAGE_SIZE = 20;
  const [docTotal, setDocTotal] = useState(0);

  // Chat state
  const [showRefs, setShowRefs] = useState(true);
  const {
    sessions, currentSession, messages, isStreaming,
    streamContent, references, streamError, retrievalStatus, retrievalStats,
    fetchSessions, createSession, deleteSession,
    setCurrentSession, fetchMessages, sendMessage, stopStreaming,
  } = useChatStore();

  // Load KB + documents
  const loadDocs = useCallback(async (page = 0) => {
    try {
      const skip = page * DOC_PAGE_SIZE;
      const data = await api<{ items: DocType[]; total: number }>(
        `/api/kbs/${kbIdNum}/documents?skip=${skip}&limit=${DOC_PAGE_SIZE}`,
      );
      setDocuments(data.items);
      setDocTotal(data.total);
      setDocPage(page);
    } catch { /* ignore */ }
    finally { setDocLoading(false); }
  }, [kbIdNum]);

  useEffect(() => {
    if (kbIdNum) {
      fetchKB(kbIdNum);
      loadDocs();
      fetchSessions(kbIdNum);
    }
  }, [kbIdNum, fetchKB, loadDocs, fetchSessions]);

  // Poll for processing docs
  useEffect(() => {
    const hasProcessing = documents.some(
      (d) => !['completed', 'failed'].includes(d.status)
    );
    if (!hasProcessing) return;
    const interval = setInterval(loadDocs, 3000);
    return () => clearInterval(interval);
  }, [documents, loadDocs]);

  // Load messages when session changes
  useEffect(() => {
    if (currentSession) { fetchMessages(currentSession.id); }
  }, [currentSession, fetchMessages]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

  // Document actions
  const handleUploaded = (doc: DocType) => {
    setDocuments((prev) => [doc, ...prev]);
    setUploadError('');
  };

  const handleUploadError = (err: unknown) => {
    setUploadError(parseApiError(err));
  };

  const handleDeleteDoc = async (docId: number) => {
    if (!confirm(t('document.confirmDelete'))) return;
    try {
      await api(`/api/kbs/${kbIdNum}/documents/${docId}`, { method: 'DELETE' });
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch { /* ignore */ }
  };

  const handleDeleteKB = async () => {
    if (!confirm(t('kb.confirmDelete'))) return;
    await deleteKB(kbIdNum);
    navigate('/dashboard');
  };

  // Chat actions
  const handleCreateSession = async () => {
    if (!kbIdNum) return;
    await createSession(kbIdNum);
  };

  const handleSelectSession = (session: ChatSession) => {
    setCurrentSession(session);
  };

  const handleDeleteSession = async (session: ChatSession) => {
    await deleteSession(session.id);
  };

  const handleSendMessage = async (content: string) => {
    if (!currentSession) return;
    await sendMessage(currentSession.id, content);
  };

  // Build display messages with streaming
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

  return (
    <div className="h-screen flex flex-col page-bg overflow-hidden">
      <header className="h-14 border-b border-surface-800/90 flex items-center px-4 gap-3 shrink-0 glass-panel rounded-none">
        <button onClick={() => navigate('/dashboard')} className="btn-ghost p-1.5" title={t('common.back')}>
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="w-8 h-8 rounded-lg bg-brand-500/15 border border-brand-500/25 flex items-center justify-center shrink-0">
          <BookOpen className="w-4 h-4 text-brand-400" />
        </div>
        <h1 className="font-display font-semibold text-surface-900 dark:text-surface-100 truncate flex-1 text-base sm:text-lg">
          {currentKB?.name || t('common.loading')}
        </h1>
        <ThemeSwitcher testId="kb-detail-theme-switcher" />
        <LangSwitcher testId="kb-detail-lang-switcher" />
        <button onClick={handleDeleteKB} className="btn-ghost p-2 text-red-400/90 hover:text-red-400" title={t('common.delete')}>
          <Trash2 className="w-4 h-4" />
        </button>
      </header>

      {currentKB && <KBPublishPanel kb={currentKB} />}

      {/* Main content: dual-pane */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT pane: Document management (~35%) */}
        <div className="w-[35%] min-w-[320px] border-r border-surface-200/90 dark:border-surface-800/90 flex flex-col overflow-hidden bg-white/50 dark:bg-surface-950/40">
          <div className="p-4 border-b border-surface-800/80">
            <p className="section-label mb-3">{t('document.upload')}</p>
            <FileUploader kbId={kbIdNum} onUploaded={handleUploaded} />
            {uploadError && (
              <p className="text-red-400 text-xs mt-2">{uploadError}</p>
            )}
          </div>

          {/* Document list */}
          <div className="flex-1 overflow-y-auto p-4">
            <p className="pane-header mb-3">
              <FileText className="w-4 h-4 text-brand-400" />
              {t('document.list')}
              <span className="text-surface-600 font-normal tabular-nums">({docTotal})</span>
            </p>

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
                      <button onClick={() => handleDeleteDoc(doc.id)}
                        className="p-1 text-surface-600 hover:text-red-400 shrink-0" title={t('common.delete')}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
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
                <button
                  type="button"
                  className="btn-ghost px-2 py-1 disabled:opacity-40"
                  disabled={docPage === 0}
                  onClick={() => loadDocs(docPage - 1)}
                >
                  {t('common.back')}
                </button>
                <span>{docPage + 1} / {Math.ceil(docTotal / DOC_PAGE_SIZE)}</span>
                <button
                  type="button"
                  className="btn-ghost px-2 py-1 disabled:opacity-40"
                  disabled={(docPage + 1) * DOC_PAGE_SIZE >= docTotal}
                  onClick={() => loadDocs(docPage + 1)}
                >
                  →
                </button>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT pane: Chat Q&A (~65%) */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Upper: chat area */}
          <div className="flex-1 flex min-h-0">
            {/* Session sidebar (narrow) */}
            <div className="w-56 border-r border-surface-200/90 dark:border-surface-800/90 shrink-0 hidden sm:block bg-surface-50/80 dark:bg-surface-950/30">
              <SessionList
                sessions={sessions}
                currentSessionId={currentSession?.id || null}
                onSelect={handleSelectSession}
                onCreate={handleCreateSession}
                onDelete={handleDeleteSession}
              />
            </div>

            {/* Messages */}
            <div className="flex-1 flex flex-col min-w-0">
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
                      onClick={handleCreateSession}
                      className="btn-primary mt-6 text-sm"
                    >
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
                        {retrievalStats.cached && (
                          <span className="ml-2 text-brand-400">(cache)</span>
                        )}
                      </div>
                    )}
                    {displayMessages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                      >
                        <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                          msg.role === 'user'
                            ? 'bg-surface-700/90 border border-surface-600'
                            : 'bg-brand-500/15 border border-brand-500/25'
                        }`}>
                          {msg.role === 'user'
                            ? <User className="w-4 h-4 text-surface-300" />
                            : <Bot className="w-4 h-4 text-brand-400" />
                          }
                        </div>
                        <div className={`flex-1 min-w-0 text-sm max-w-[85%] ${
                          msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'
                        }`}>
                          {msg.role === 'assistant' ? (
                            <MarkdownRenderer content={msg.content} />
                          ) : (
                            <div className="text-surface-100 leading-relaxed whitespace-pre-wrap break-words">
                              {msg.content}
                            </div>
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

              {/* Chat input */}
              {currentSession && (
                <ChatInput onSend={handleSendMessage} onStop={stopStreaming} isStreaming={isStreaming} />
              )}
            </div>

            {/* References panel (right side of chat) */}
            {showRefs && (
              <div className="w-64 border-l border-surface-200/90 dark:border-surface-800/90 shrink-0 hidden xl:block overflow-y-auto bg-surface-50/80 dark:bg-surface-950/40">
                <div className="flex items-center justify-between px-3 py-3 border-b border-surface-800/80">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-surface-500">{t('chat.references')}</h3>
                  <button onClick={() => setShowRefs(false)} className="btn-ghost p-1" title={t('chat.hideRefs')}>
                    <PanelRightClose className="w-3.5 h-3.5" />
                  </button>
                </div>
                <ReferencePanel references={references} onReferenceClick={handleReferenceClick} />
              </div>
            )}
            {!showRefs && (
              <button onClick={() => setShowRefs(true)}
                className="self-start mt-3 mr-3 btn-ghost p-1.5 shrink-0 hidden xl:block"
                title={t('chat.showRefs')}>
                <PanelRightOpen className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

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
