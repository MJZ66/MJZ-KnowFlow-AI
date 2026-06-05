import { useTranslation } from 'react-i18next';
import { FileText, Hash } from 'lucide-react';
import type { SSEReference } from '../types';

interface Props {
  references: SSEReference[];
  onReferenceClick?: (ref: SSEReference) => void;
}

/** Check if a section_title looks like noise (CLI, paths, code wrappers) */
export function isNoiseSectionTitle(title: string | null | undefined): boolean {
  if (!title || title.length < 3 || title.length > 200) return true;

  const noisePatterns = [
    /^cd\s/i, /^docker/i, /^npm\s/i, /^pip\s/i, /^git\s/i,
    /^curl\s/i, /^wget\s/i, /^psql\s/i, /^uvicorn/i, /^alembic/i,
    /^PS\s/i, /^Get-/i, /^Set-/i, /^Write-/i, /^Remove-/i,
    /^Select-/i, /^New-/i, /^Copy-/i, /^Invoke-/i, /^Start-/i,
    /^Stop-/i, /^[A-Z]:[\\/]/i, /^@['"]/, /^['"]@/,
    /^[\\/]/, /^\.\.?[\\/]/, /^\{/, /^\(/, /^</,
    /^['"\]]/, /^[-=_]{3,}$/,
  ];

  for (const p of noisePatterns) {
    if (p.test(title)) return true;
  }
  return false;
}

export default function ReferencePanel({ references, onReferenceClick }: Props) {
  const { t } = useTranslation();

  if (references.length === 0) {
    return (
      <div className="p-6 text-center">
        <FileText className="w-8 h-8 mx-auto text-surface-600 mb-2" />
        <p className="text-surface-500 text-sm">{t('chat.noReferences')}</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <h3 className="text-sm font-semibold text-surface-700 dark:text-surface-300 flex items-center gap-2">
        <Hash className="w-4 h-4" />
        {t('chat.references')} ({references.length})
      </h3>
      {references.map((ref, i) => {
        const showSectionTitle = !isNoiseSectionTitle(ref.section_title);
        const preview = ref.content_preview || '';
        const truncated = preview.length > 200 ? preview.slice(0, 200) + '...' : preview;

        return (
          <button
            key={i}
            type="button"
            data-testid={`reference-card-${i}`}
            onClick={() => onReferenceClick?.(ref)}
            disabled={!onReferenceClick || !ref.document_id}
            className={`w-full text-left bg-white border border-surface-200 rounded-xl p-3 space-y-1.5 transition-all duration-200 dark:bg-surface-900/80 dark:border-surface-700/60 ${
              onReferenceClick && ref.document_id
                ? 'hover:border-brand-500/35 hover:bg-surface-50 hover:shadow-sm cursor-pointer dark:hover:bg-surface-800/90'
                : 'hover:border-surface-300 dark:hover:border-surface-600/50'
            }`}
          >
            {/* Header: filename + score */}
            <div className="flex items-center gap-2 text-xs">
              <FileText className="w-3.5 h-3.5 text-brand-400 shrink-0" />
              <span className="font-medium text-surface-300 truncate flex-1">
                {ref.source_filename || t('chat.sourceUnknown')}
              </span>
              {(ref.score !== null && ref.score !== undefined) && (
                <span className="text-surface-500 shrink-0 tabular-nums">
                  {t('chat.score')}: {(ref.score * 100).toFixed(0)}%
                </span>
              )}
            </div>

            {/* Metadata: page + section */}
            <div className="flex gap-2 text-xs text-surface-500 flex-wrap">
              {ref.page_number && <span>{t('chat.page', { page: ref.page_number })}</span>}
              {showSectionTitle && (
                <>
                  {ref.page_number && <span className="text-surface-600">|</span>}
                  <span className="truncate max-w-[200px]">{ref.section_title}</span>
                </>
              )}
            </div>

            {/* Content preview */}
            {truncated && (
              <p className="text-xs text-surface-500 line-clamp-3 leading-relaxed mt-1">{truncated}</p>
            )}
          </button>
        );
      })}
    </div>
  );
}
