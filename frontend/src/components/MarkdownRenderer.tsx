/**
 * Simple Markdown renderer for chat messages.
 * Supports: headings, bold, italic, lists, code blocks, links, line breaks.
 * Lightweight — no external dependencies.
 */

import { useMemo } from 'react';

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function renderMarkdown(text: string): string {
  let html = escapeHtml(text);

  // Code blocks (``` ... ```)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g,
    '<pre class="bg-surface-800 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono text-surface-300"><code>$2</code></pre>');

  // Inline code (`...`)
  html = html.replace(/`([^`]+)`/g,
    '<code class="bg-surface-800 text-brand-300 px-1.5 py-0.5 rounded text-xs font-mono">$1</code>');

  // Bold (**...** or __...__)
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-surface-100">$1</strong>');
  html = html.replace(/__([^_]+)__/g, '<strong class="font-semibold text-surface-100">$1</strong>');

  // Italic (*...*)
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Headings (### ...)
  html = html.replace(/^### (.+)$/gm, '<h4 class="text-surface-100 font-semibold mt-3 mb-1">$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3 class="text-surface-100 font-semibold text-lg mt-4 mb-1">$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2 class="text-surface-100 font-bold text-xl mt-4 mb-2">$1</h2>');

  // Unordered lists
  html = html.replace(/^[\-\*]\s+(.+)$/gm, '<li class="ml-4 list-disc text-surface-200">$1</li>');
  // Ordered lists
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li class="ml-4 list-decimal text-surface-200">$1</li>');

  // Horizontal rules
  html = html.replace(/^---+$/gm, '<hr class="border-surface-700 my-3" />');

  // Blockquotes
  html = html.replace(/^&gt;\s?(.+)$/gm, '<blockquote class="border-l-2 border-brand-500 pl-3 italic text-surface-400 my-2">$1</blockquote>');

  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" class="text-brand-400 hover:text-brand-300 underline" target="_blank" rel="noopener">$1</a>');

  // Line breaks (double newline → paragraph)
  html = html.replace(/\n\n/g, '</p><p class="mb-2">');

  // Wrap in paragraph
  html = '<p class="mb-2">' + html + '</p>';

  // Clean up empty paragraphs
  html = html.replace(/<p class="mb-2"><\/p>/g, '');

  return html;
}

export default function MarkdownRenderer({ content }: { content: string }) {
  const html = useMemo(() => renderMarkdown(content), [content]);

  return (
    <div
      className="prose-sm prose-invert max-w-none"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
