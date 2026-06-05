import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, FileText, Loader2 } from 'lucide-react';
import { api } from '../api/client';
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
  status: string;
  chunks: DocumentChunkPreview[];
}

export interface DocumentPreviewPanelProps {
  documentId: number | null;
  targetChunkId?: number | null;
  targetChunkIndex?: number | null;
  open: boolean;
  onClose: () => void;
}

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
  const [highlightId, setHighlightId] = useState<number | null>(null);
  const chunkRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!open || !documentId) {
      setData(null);
      setError('');
      setHighlightId(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError('');

    api<DocumentChunksResponse>(`/api/documents/${documentId}/chunks`)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(parseApiError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [open, documentId]);

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

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="document-preview-panel">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden />
      <aside className="relative w-full max-w-lg h-full bg-white dark:bg-surface-900 border-l border-surface-200 dark:border-surface-700 flex flex-col shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-200 dark:border-surface-800">
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="w-5 h-5 text-brand-600 dark:text-brand-400 shrink-0" />
            <h2 className="text-sm font-semibold text-surface-900 dark:text-surface-100 truncate">
              {t('preview.title')}
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
          {loading && (
            <div className="flex items-center justify-center gap-2 text-surface-400 py-12">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">{t('preview.loading')}</span>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-400 text-center py-8">{error || t('preview.error')}</p>
          )}

          {!loading && !error && data && (
            <>
              <div className="mb-4 space-y-2">
                <p className="text-sm font-medium text-surface-800 dark:text-surface-200 truncate">{data.filename}</p>
                <DocumentStatusBadge status={data.status as DocumentStatus} />
              </div>

              {data.chunks.length === 0 ? (
                <p className="text-sm text-surface-500 text-center py-8">{t('preview.noChunks')}</p>
              ) : (
                <div className="space-y-3">
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
