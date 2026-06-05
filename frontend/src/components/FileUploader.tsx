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
}

const ALLOWED_TYPES = ['.pdf', '.docx', '.md', '.txt'];

export default function FileUploader({ kbId, onUploaded, disabled }: FileUploaderProps) {
  const { t } = useTranslation();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [uploadProgress, setUploadProgress] = useState(0);

  const handleUpload = useCallback(async (file: File) => {
    setError(null);
    setUploading(true);
    setUploadProgress(0);
    setSelectedFile(file);
    try {
      const doc = await uploadFileWithProgress<Document>(
        `/api/kbs/${kbId}/documents/upload`,
        file,
        setUploadProgress,
      );
      onUploaded(doc);
      setSelectedFile(null);
      setUploadProgress(0);
    } catch (err: unknown) {
      setError(parseApiError(err));
    } finally {
      setUploading(false);
    }
  }, [kbId, onUploaded]);

  const onDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }, [handleUpload]);

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
        onClick={() => {
          if (disabled) return;
          const input = document.createElement('input');
          input.type = 'file';
          input.accept = ALLOWED_TYPES.join(',');
          input.onchange = (e) => {
            const f = (e.target as HTMLInputElement).files?.[0];
            if (f) handleUpload(f);
          };
          input.click();
        }}
      >
        {uploading ? (
          <div className="space-y-3">
            <div className="w-10 h-10 mx-auto rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            <p className="text-surface-200 font-medium">{t('document.uploading')}</p>
            {selectedFile && <p className="text-surface-500 text-sm truncate max-w-xs mx-auto">{selectedFile.name}</p>}
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
            <p className="text-surface-500 text-xs">{t('document.uploadTypes')}</p>
          </div>
        )}
      </div>
      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/5 border border-red-500/20 rounded-lg p-3">
          <X className="w-4 h-4 shrink-0" />
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
