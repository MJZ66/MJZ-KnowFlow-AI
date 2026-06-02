import { Bot } from 'lucide-react';

interface Props {
  content: string;
  isStreaming: boolean;
}

export default function StreamingMessage({ content, isStreaming }: Props) {
  if (!content && !isStreaming) return null;

  return (
    <div className="flex gap-3 py-4">
      <div className="w-8 h-8 rounded-lg bg-brand-500/10 flex items-center justify-center shrink-0">
        <Bot className="w-4 h-4 text-brand-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-surface-200 leading-relaxed whitespace-pre-wrap break-words">
          {content || ''}
          {isStreaming && (
            <span className="inline-block w-2 h-5 ml-0.5 bg-brand-400 animate-pulse rounded-sm align-text-bottom" />
          )}
        </div>
      </div>
    </div>
  );
}
