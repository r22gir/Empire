'use client';
import { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Square, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useDeskChat } from '@/hooks/useDeskChat';
import { BUSINESS_DESKS } from '@/lib/deskData';
import { ToolResultCard } from './shared';

interface DeskChatProps {
  deskId: string;
}

export default function DeskChat({ deskId }: DeskChatProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const chat = useDeskChat({ deskId });
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const deskDef = BUSINESS_DESKS.find(d => d.id === deskId);
  const deskColor = deskDef?.color || '#D4AF37';

  // Auto-scroll on new messages / streaming
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [chat.messages, chat.streamingContent]);

  // Focus input when opened
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const handleSend = () => {
    if (!input.trim()) return;
    chat.sendMessage(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Collapsed: floating button
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition hover:scale-110"
        style={{ background: deskColor, color: '#0a0a0a' }}
        title="Open desk chat"
      >
        <MessageSquare className="w-5 h-5" />
      </button>
    );
  }

  // Expanded panel
  return (
    <div
      className="w-[380px] shrink-0 flex flex-col h-full"
      style={{ background: 'var(--surface)', borderLeft: '1px solid var(--border)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 shrink-0"
        style={{ borderBottom: `2px solid ${deskColor}` }}
      >
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4" style={{ color: deskColor }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            {deskDef?.name || deskId} Chat
          </span>
        </div>
        <div className="flex items-center gap-1">
          {chat.messages.length > 0 && (
            <button
              onClick={chat.clearMessages}
              className="p-1.5 rounded-lg transition"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={e => { e.currentTarget.style.color = '#ef4444'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; }}
              title="Clear chat"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={() => setOpen(false)}
            className="p-1.5 rounded-lg transition"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {chat.messages.length === 0 && !chat.streamingContent && (
          <div className="text-center py-8">
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Ask MAX anything about {deskDef?.name || deskId}
            </p>
          </div>
        )}

        {chat.messages.map((msg, i) => (
          <div key={i} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            {msg.role === 'user' ? (
              <div
                className="max-w-[85%] rounded-xl rounded-br-sm px-3 py-2 text-xs"
                style={{
                  background: `linear-gradient(135deg, ${deskColor}ee, ${deskColor})`,
                  color: '#0a0a0a',
                }}
              >
                <p className="whitespace-pre-wrap leading-relaxed font-medium">{msg.content}</p>
              </div>
            ) : (
              <div
                className="max-w-[90%] rounded-xl rounded-bl-sm px-3 py-2"
                style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}
              >
                <div className="desk-chat-markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
                {msg.toolResults?.map((tr, j) => (
                  <ToolResultCard key={j} result={tr} />
                ))}
                {msg.model && (
                  <p className="text-[10px] mt-1.5 font-mono" style={{ color: 'var(--text-muted)' }}>
                    via {msg.model}
                  </p>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Streaming message */}
        {chat.isStreaming && chat.streamingContent && (
          <div className="flex justify-start">
            <div
              className="max-w-[90%] rounded-xl rounded-bl-sm px-3 py-2"
              style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}
            >
              <div className="desk-chat-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{chat.streamingContent}</ReactMarkdown>
                <span className="streaming-cursor" />
              </div>
            </div>
          </div>
        )}

        {/* Streaming dots before text arrives */}
        {chat.isStreaming && !chat.streamingContent && (
          <div className="flex justify-start">
            <div
              className="rounded-xl px-4 py-3 flex gap-1"
              style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}
            >
              <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: deskColor, animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: deskColor, animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: deskColor, animationDelay: '300ms' }} />
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 shrink-0" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${deskDef?.name || 'MAX'}...`}
            className="flex-1 rounded-lg px-3 py-2 text-xs resize-none outline-none"
            style={{
              background: 'var(--raised)',
              border: '1px solid var(--border)',
              color: 'var(--text-primary)',
              maxHeight: '80px',
            }}
            rows={1}
            disabled={chat.isStreaming}
          />
          {chat.isStreaming ? (
            <button
              onClick={chat.stopStreaming}
              className="px-3 rounded-lg flex items-center justify-center transition"
              style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.25)' }}
            >
              <Square className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="px-3 rounded-lg flex items-center justify-center transition"
              style={{
                background: input.trim() ? deskColor : 'var(--elevated)',
                color: input.trim() ? '#0a0a0a' : 'var(--text-muted)',
              }}
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
