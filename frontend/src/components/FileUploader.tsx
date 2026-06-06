import { useCallback, useState, type DragEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Upload, FileText, X } from 'lucide-react';
import { uploadFileWithProgress } from '../api/client';
import { parseApiError } from '../utils/error';
import type { Document } from '../types';

interface FileUploaderProps {
  kbId: number;
  onUploaded: (doc: Document) => void;
  disabled?: boolean;
  multiple?: boolean;
}

const ALLOWED_TYPES = ['.pdf', '.docx', '.md', '.txt'];

function isAllowedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ALLOWED_TYPES.some((ext) => name.endsWith(ext));
}

export default function FileUploader({ kbId, onUploaded, disabled, multiple = true }: FileUploaderProps) {
  const { t } = useTranslation();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentFile, setCurrentFile] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [batchIndex, setBatchIndex] = useState(0);
  const [batchTotal, setBatchTotal] = useState(0);

  const uploadFiles = useCallback(async (files: File[]) => {
    const valid = files.filter(isAllowedFile);
    if (valid.length === 0) {
      setError(t('document.invalidType'));
      return;
    }

    setError(null);
    setUploading(true);
    setBatchTotal(valid.length);
    setBatchIndex(0);

    const errors: string[] = [];

    for (let i = 0; i < valid.length; i++) {
      const file = valid[i];
      setBatchIndex(i + 1);
      setCurrentFile(file.name);
      setUploadProgress(0);
      try {
        const doc = await uploadFileWithProgress<Document>(
          `/api/kbs/${kbId}/documents/upload`,
          file,
          setUploadProgress,
        );
        onUploaded(doc);
      } catch (err: unknown) {
        errors.push(`${file.name}: ${parseApiError(err)}`);
      }
    }

    setCurrentFile(null);
    setUploadProgress(0);
    setBatchIndex(0);
    setBatchTotal(0);
    setUploading(false);

    if (errors.length > 0) {
      setError(errors.join('\n'));
    }
  }, [kbId, onUploaded, t]);

  const onDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) void uploadFiles(files);
  }, [uploadFiles]);

  const openPicker = () => {
    if (disabled || uploading) return;
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = ALLOWED_TYPES.join(',');
    input.multiple = multiple;
    input.onchange = (e: Event) => {
      const list = (e.target as HTMLInputElement).files;
      if (list?.length) void uploadFiles(Array.from(list));
    };
    input.click();
  };

  return (
    <div className="space-y-3">
      <div
        onDrop={onDrop}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        className={`relative border-2 border-dashed rounded-xl p-6 text-center transition-all duration-300 ${
          isDragging
            ? 'border-brand-500 bg-brand-500/10 scale-[1.01] shadow-glow'
            : 'border-surface-700 hover:border-brand-600/40 bg-surface-900/40'
        } ${disabled ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}`}
        onClick={openPicker}
        data-testid="file-uploader"
      >
        {uploading ? (
          <div className="space-y-3">
            <div className="w-10 h-10 mx-auto rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            <p className="text-surface-200 font-medium">{t('document.uploading')}</p>
            {batchTotal > 1 && (
              <p className="text-surface-500 text-xs">
                {t('document.uploadBatch', { current: batchIndex, total: batchTotal })}
              </p>
            )}
            {currentFile && <p className="text-surface-500 text-sm truncate max-w-xs mx-auto">{currentFile}</p>}
            <div className="max-w-xs mx-auto">
              <div className="h-1.5 bg-surface-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-600 to-brand-400 transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-surface-500 text-xs mt-1 tabular-nums">{uploadProgress}%</p>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="w-12 h-12 mx-auto rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
              <Upload className="w-6 h-6 text-brand-400" />
            </div>
            <p className="text-surface-200 font-medium text-sm">{t('document.uploadHint')}</p>
            <p className="text-surface-500 text-xs">
              {multiple ? t('document.uploadHintMultiple') : t('document.uploadTypes')}
            </p>
          </div>
        )}
      </div>
      {error && (
        <div className="flex items-start gap-2 text-red-400 text-sm bg-red-500/5 border border-red-500/20 rounded-lg p-3 whitespace-pre-wrap">
          <X className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
      <div className="flex flex-wrap gap-2 text-xs text-surface-500">
        {ALLOWED_TYPES.map((ext) => (
          <span key={ext} className="flex items-center gap-1 px-2 py-1 bg-surface-800/80 border border-surface-700 rounded-md font-mono">
            <FileText className="w-3 h-3 text-brand-500/80" />
            {ext}
          </span>
        ))}
      </div>
    </div>
  );
}
