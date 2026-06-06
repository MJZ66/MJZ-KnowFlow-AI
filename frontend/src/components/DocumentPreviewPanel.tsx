import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, FileText, Loader2, ImageIcon } from 'lucide-react';
import { api, fetchDocumentBlob } from '../api/client';
import { parseApiError } from '../utils/error';
import DocumentStatusBadge from './DocumentStatusBadge';
import type { DocumentStatus } from '../types';

export interface DocumentChunkPreview {
  id: number;
  chunk_index: number;
  content: string;
  page_number: number | null;
  section_title: string | null;
  metadata: Record<string, unknown>;
}

interface DocumentChunksResponse {
  document_id: number;
  filename: string;
  file_type?: string;
  preview_kind?: 'text' | 'image' | 'pdf';
  status: string;
  progress?: number;
  error_message?: string | null;
  chunks: DocumentChunkPreview[];
}

export interface DocumentPreviewPanelProps {
  documentId: number | null;
  targetChunkId?: number | null;
  targetChunkIndex?: number | null;
  open: boolean;
  onClose: () => void;
}

const TERMINAL_STATUSES = new Set(['completed', 'failed']);
const VISUAL_PREVIEW_KINDS = new Set(['image', 'pdf']);

export default function DocumentPreviewPanel({
  documentId,
  targetChunkId,
  targetChunkIndex,
  open,
  onClose,
}: DocumentPreviewPanelProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<DocumentChunksResponse | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [highlightId, setHighlightId] = useState<number | null>(null);
  const chunkRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const fetchPreview = useCallback(async (silent = false) => {
    if (!documentId) return;
    if (!silent) {
      setLoading(true);
      setError('');
    }
    try {
      const res = await api<DocumentChunksResponse>(`/api/documents/${documentId}/chunks`);
      setData(res);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      if (!silent) setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    if (!open || !documentId) {
      setData(null);
      setError('');
      setHighlightId(null);
      return;
    }
    void fetchPreview(false);
  }, [open, documentId, fetchPreview]);

  useEffect(() => {
    if (!open || !documentId || !data?.status) return;
    if (TERMINAL_STATUSES.has(data.status)) return;

    const timer = window.setInterval(() => {
      void fetchPreview(true);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [open, documentId, data?.status, fetchPreview]);

  useEffect(() => {
    if (!open || !documentId || data?.status !== 'completed') {
      setFileUrl(null);
      return;
    }

    const kind = data.preview_kind ?? 'text';
    if (!VISUAL_PREVIEW_KINDS.has(kind)) {
      setFileUrl(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;

    const loadFile = async () => {
      setFileLoading(true);
      try {
        const blob = await fetchDocumentBlob(`/api/documents/${documentId}/file`);
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setFileUrl(objectUrl);
      } catch (err) {
        if (!cancelled) {
          setError(parseApiError(err));
        }
      } finally {
        if (!cancelled) setFileLoading(false);
      }
    };

    void loadFile();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setFileUrl(null);
    };
  }, [open, documentId, data?.status, data?.preview_kind]);

  useEffect(() => {
    if (!data?.chunks.length || !open) return;

    let target: DocumentChunkPreview | undefined;
    if (targetChunkId != null) {
      target = data.chunks.find((c) => c.id === targetChunkId);
    }
    if (!target && targetChunkIndex != null) {
      target = data.chunks.find((c) => c.chunk_index === targetChunkIndex);
    }

    if (!target) return;

    const el = chunkRefs.current[target.id];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setHighlightId(target.id);
      const timer = window.setTimeout(() => setHighlightId(null), 2000);
      return () => window.clearTimeout(timer);
    }
  }, [data, open, targetChunkId, targetChunkIndex]);

  if (!open) return null;

  const isProcessing = data?.status && !TERMINAL_STATUSES.has(data.status);
  const previewKind = data?.preview_kind ?? 'text';
  const showVisualPreview = data?.status === 'completed' && VISUAL_PREVIEW_KINDS.has(previewKind);
  const showTextChunks = data?.status === 'completed' && (previewKind === 'text' || data.chunks.length > 0);

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="document-preview-panel">
      <div className="absolute inset-0 bg-black/50 modal-backdrop preview-backdrop" onClick={onClose} aria-hidden />
      <aside className="preview-drawer relative w-full max-w-lg h-full bg-white dark:bg-surface-900 border-l border-surface-200 dark:border-surface-700 flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-200 dark:border-surface-800">
          <div className="flex items-center gap-2 min-w-0">
            {previewKind === 'image' ? (
              <ImageIcon className="w-5 h-5 text-brand-600 dark:text-brand-400 shrink-0" />
            ) : (
              <FileText className="w-5 h-5 text-brand-600 dark:text-brand-400 shrink-0" />
            )}
            <h2 className="text-sm font-semibold text-surface-900 dark:text-surface-100 truncate">
              {data?.filename || t('preview.title')}
            </h2>
          </div>
          <button
            type="button"
            data-testid="preview-close"
            onClick={onClose}
            className="btn-ghost p-1.5"
            title={t('preview.close')}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {loading && !data && (
            <div className="flex items-center justify-center gap-2 text-surface-400 py-12">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">{t('preview.loading')}</span>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-400 text-center py-8">{error || t('preview.error')}</p>
          )}

          {!error && data && (
            <>
              <div className="mb-4 space-y-2">
                <p className="text-sm font-medium text-surface-800 dark:text-surface-200 truncate">{data.filename}</p>
                <DocumentStatusBadge status={data.status as DocumentStatus} />
              </div>

              {data.status === 'failed' && data.error_message && (
                <p className="text-sm text-red-400 bg-red-500/5 border border-red-500/20 rounded-lg p-3 mb-4">
                  {data.error_message}
                </p>
              )}

              {isProcessing && (
                <div className="text-center py-10 space-y-4">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-400 mx-auto" />
                  <p className="text-sm text-surface-500">{t('preview.processing')}</p>
                  <div className="max-w-xs mx-auto">
                    <div className="h-1.5 bg-surface-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-500 transition-all duration-300"
                        style={{ width: `${Math.max(0, Math.min(100, data.progress ?? 0))}%` }}
                      />
                    </div>
                    <p className="text-xs text-surface-500 mt-1 tabular-nums">{data.progress ?? 0}%</p>
                  </div>
                </div>
              )}

              {showVisualPreview && (
                <div className="mb-4">
                  {fileLoading && (
                    <div className="flex items-center justify-center gap-2 text-surface-400 py-8">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span className="text-sm">{t('preview.loadingFile')}</span>
                    </div>
                  )}
                  {!fileLoading && fileUrl && previewKind === 'image' && (
                    <img
                      src={fileUrl}
                      alt={data.filename}
                      className="w-full max-h-[420px] object-contain rounded-lg border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800/40"
                      data-testid="preview-image"
                    />
                  )}
                  {!fileLoading && fileUrl && previewKind === 'pdf' && (
                    <iframe
                      src={fileUrl}
                      title={data.filename}
                      className="w-full h-[480px] rounded-lg border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800/40"
                      data-testid="preview-pdf"
                    />
                  )}
                </div>
              )}

              {data.status === 'completed' && previewKind === 'text' && data.chunks.length === 0 && (
                <p className="text-sm text-surface-500 text-center py-8">{t('preview.noChunks')}</p>
              )}

              {showTextChunks && data.chunks.length > 0 && (
                <div className="space-y-3">
                  {previewKind !== 'text' && (
                    <p className="text-xs font-medium text-surface-500 uppercase tracking-wide">
                      {t('preview.extractedText')}
                    </p>
                  )}
                  {data.chunks.map((chunk) => (
                    <div
                      key={chunk.id}
                      ref={(el) => { chunkRefs.current[chunk.id] = el; }}
                      data-testid={`preview-chunk-${chunk.id}`}
                      className={`rounded-lg border p-3 transition-colors ${
                        highlightId === chunk.id
                          ? 'border-brand-500 bg-brand-500/10 ring-1 ring-brand-400/50'
                          : 'border-surface-200 bg-surface-50 dark:border-surface-700 dark:bg-surface-800/40'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs text-surface-400 mb-2">
                        <span>{t('preview.chunk', { index: chunk.chunk_index + 1 })}</span>
                        {chunk.page_number != null && (
                          <span>{t('chat.page', { page: chunk.page_number })}</span>
                        )}
                      </div>
                      {chunk.section_title && (
                        <p className="text-xs text-surface-500 mb-1 truncate">{chunk.section_title}</p>
                      )}
                      <p className="text-sm text-surface-700 dark:text-surface-300 whitespace-pre-wrap leading-relaxed">
                        {chunk.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
