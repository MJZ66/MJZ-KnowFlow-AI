import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, Square } from 'lucide-react';

interface Props {
  onSend: (content: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  disabled?: boolean;
}

export default function ChatInput({ onSend, onStop, isStreaming, disabled }: Props) {
  const { t } = useTranslation();
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className="border-t border-surface-200/90 dark:border-surface-800/90 p-4 bg-white/90 dark:bg-surface-950/90 backdrop-blur-xl">
      <div className="flex items-end gap-2 max-w-3xl mx-auto rounded-2xl border border-surface-200 bg-surface-50/90 dark:border-surface-800 dark:bg-surface-900/60 p-2 shadow-card focus-within:border-brand-500/40 dark:focus-within:border-brand-600/30 focus-within:ring-2 focus-within:ring-brand-500/15 transition-all">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('chat.placeholder')}
          disabled={disabled}
          rows={1}
          className="input-field resize-none flex-1 border-0 bg-transparent focus:ring-0 focus:border-transparent shadow-none"
        />
        {isStreaming ? (
          <button onClick={onStop} className="btn-danger p-2.5 shrink-0" title={t('chat.stop')}>
            <Square className="w-5 h-5" />
          </button>
        ) : (
          <button onClick={handleSend} disabled={!value.trim() || disabled} className="btn-primary p-2.5 shrink-0" title={t('chat.send')}>
            <Send className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
}
