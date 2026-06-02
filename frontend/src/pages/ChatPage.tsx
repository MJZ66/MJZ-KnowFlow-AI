import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  BookOpen, ArrowLeft, User, Bot, PanelRightClose, PanelRightOpen,
} from 'lucide-react';
import { useKBStore } from '../stores/kbStore';
import { useChatStore } from '../stores/chatStore';
import SessionList from '../components/SessionList';
import ChatInput from '../components/ChatInput';
import ReferencePanel from '../components/ReferencePanel';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { parseApiError } from '../utils/error';
import type { ChatSession, ChatMessage } from '../types';

export default function ChatPage() {
  const { t } = useTranslation();
  const { kbId } = useParams<{ kbId: string }>();
  const kbIdNum = Number(kbId);
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showRefs, setShowRefs] = useState(true);
  const { currentKB, fetchKB } = useKBStore();
  const {
    sessions, currentSession,
    messages, isStreaming, streamContent, references, streamError, retrievalStatus,
    fetchSessions, createSession, deleteSession, setCurrentSession,
    fetchMessages, sendMessage, stopStreaming,
  } = useChatStore();

  useEffect(() => {
    if (kbIdNum) { fetchKB(kbIdNum); fetchSessions(kbIdNum); }
  }, [kbIdNum, fetchKB, fetchSessions]);

  useEffect(() => {
    if (currentSession) { fetchMessages(currentSession.id); }
  }, [currentSession, fetchMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

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

  const displayMessages: (ChatMessage & { isStreaming?: boolean })[] = [...messages];
  if (isStreaming && streamContent) {
    displayMessages.push({
      id: -1, session_id: currentSession?.id || 0, user_id: 0,
      role: 'assistant', content: streamContent,
      created_at: new Date().toISOString(), isStreaming: true,
    });
  }

  return (
    <div className="h-screen flex flex-col bg-surface-950">
      <header className="h-14 border-b border-surface-800 flex items-center px-4 gap-4 shrink-0 bg-surface-950/80 backdrop-blur-xl">
        <button onClick={() => navigate(`/kbs/${kbIdNum}`)} className="btn-ghost p-1.5" title={t('common.back')}>
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-2 min-w-0">
          <BookOpen className="w-4 h-4 text-brand-400 shrink-0" />
          <h2 className="font-semibold text-surface-200 truncate">{currentKB?.name || t('common.loading')}</h2>
        </div>
        <div className="flex-1" />
        <button onClick={() => setShowRefs(!showRefs)} className="btn-ghost p-1.5" title={showRefs ? t('chat.hideRefs') : t('chat.showRefs')}>
          {showRefs ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
        </button>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar */}
        <div className="w-64 border-r border-surface-800 shrink-0 hidden md:block">
          <SessionList
            sessions={sessions}
            currentSessionId={currentSession?.id || null}
            onSelect={handleSelectSession}
            onCreate={handleCreateSession}
            onDelete={handleDeleteSession}
          />
        </div>

        {/* Center chat */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto px-4 py-6">
            {!currentSession ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Bot className="w-16 h-16 text-surface-700 mb-4" />
                <h3 className="text-xl font-semibold text-surface-300 mb-2">{t('chat.startChat')}</h3>
                <p className="text-surface-500 text-sm mb-4">{t('chat.startHint')}</p>
                <button onClick={handleCreateSession} className="btn-primary">{t('chat.newSession')}</button>
              </div>
            ) : displayMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <Bot className="w-12 h-12 text-surface-700 mb-3" />
                <p className="text-surface-500 text-sm">{t('chat.inputHint')}</p>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto space-y-2">
                {/* Retrieval status banner */}
                {retrievalStatus && (
                  <div className="flex items-center gap-2 text-sm text-brand-400 bg-brand-500/5 border border-brand-500/20 rounded-lg px-4 py-2 animate-pulse">
                    <span className="w-2 h-2 rounded-full bg-brand-400" />
                    {retrievalStatus}
                  </div>
                )}
                {displayMessages.map((msg, i) => (
                  <div key={msg.id} className={`flex gap-3 py-3 ${msg.role === 'user' ? '' : 'bg-surface-900/50 -mx-4 px-4 rounded-lg'}`}>
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${msg.role === 'user' ? 'bg-surface-700' : 'bg-brand-500/10'}`}>
                      {msg.role === 'user' ? <User className="w-3.5 h-3.5 text-surface-400" /> : <Bot className="w-3.5 h-3.5 text-brand-400" />}
                    </div>
                    <div className="flex-1 min-w-0 text-sm">
                      {msg.role === 'assistant' ? (
                        <MarkdownRenderer content={msg.content} />
                      ) : (
                        <div className="text-surface-200 leading-relaxed whitespace-pre-wrap break-words">
                          {msg.content}
                        </div>
                      )}
                      {msg.isStreaming && (
                        <span className="inline-block w-2 h-4 bg-brand-400 animate-pulse rounded-sm align-text-bottom" />
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
          {currentSession && (
            <ChatInput onSend={handleSendMessage} onStop={stopStreaming} isStreaming={isStreaming} />
          )}
        </div>

        {/* Right references */}
        {showRefs && (
          <div className="w-72 border-l border-surface-800 shrink-0 hidden lg:block overflow-y-auto">
            <ReferencePanel references={references} />
          </div>
        )}
      </div>
    </div>
  );
}
