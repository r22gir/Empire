'use client';
import { useRef, useEffect } from 'react';
import { Message, AIModel } from '@/lib/types';
import { Brain, WifiOff } from 'lucide-react';

interface Props {
  isStreaming: boolean;
  streamingContent: string;
  messages: Message[];
  backendOnline: boolean;
  selectedModel: string;
  models: AIModel[];
}

export default function MaxSection({ isStreaming, streamingContent, messages, backendOnline, selectedModel, models }: Props) {
  const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant');
  const currentModel = models.find(m => m.id === selectedModel);
  const modelLabel = currentModel?.name || selectedModel;
  const scrollRef = useRef<HTMLDivElement>(null);

  const statusText = !backendOnline
    ? 'Offline'
    : isStreaming
      ? streamingContent ? 'Speaking...' : 'Thinking...'
      : 'Online';

  const statusColor = !backendOnline
    ? '#ef4444'
    : isStreaming ? 'var(--gold)' : '#22c55e';

  // Auto-scroll during streaming
  useEffect(() => {
    if (isStreaming && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isStreaming, streamingContent]);

  return (
    <div
      className="rounded-2xl p-5 flex flex-col"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)', minHeight: 0 }}
    >
      <div className="flex items-start gap-4 shrink-0">
        {/* Animated avatar */}
        <div className="relative shrink-0">
          <div
            className={`w-16 h-16 rounded-full flex items-center justify-center ${
              isStreaming ? 'max-avatar-streaming' : 'max-avatar-glow'
            }`}
            style={{
              background: 'linear-gradient(135deg, #D4AF37 0%, #8B5CF6 100%)',
              border: '2px solid var(--gold)',
            }}
          >
            <Brain className="w-7 h-7 text-white" />
          </div>
          {/* Status dot */}
          <div
            className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full"
            style={{
              background: statusColor,
              border: '2.5px solid var(--surface)',
              animation: isStreaming ? 'pulse-online 1.5s infinite' : backendOnline ? 'pulse-online 2.2s infinite' : 'none',
            }}
          />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 mb-1">
            <span className="font-bold text-lg text-gold-shimmer tracking-wide">MAX</span>
            <span
              className="text-[10px] px-2 py-0.5 rounded-full font-mono"
              style={{
                background: 'var(--purple-pale)',
                color: 'var(--purple)',
                border: '1px solid var(--purple-border)',
              }}
            >
              {modelLabel}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: statusColor }}
            />
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {statusText}
            </span>
            {!backendOnline && (
              <WifiOff className="w-3 h-3" style={{ color: '#ef4444' }} />
            )}
          </div>
        </div>
      </div>

      {/* Response area — scrollable, fills available space */}
      <div
        ref={scrollRef}
        className="mt-3 flex-1 overflow-y-auto"
        style={{ maxHeight: '45vh', minHeight: '60px' }}
      >
        {/* Typing indicator */}
        {isStreaming && !streamingContent && (
          <div className="typing-shimmer h-2 w-24 rounded-full" style={{ background: 'var(--elevated)' }} />
        )}

        {/* Streaming content — full, not truncated */}
        {isStreaming && streamingContent && (
          <div
            className="text-xs leading-relaxed whitespace-pre-wrap break-words"
            style={{ color: 'var(--text-secondary)' }}
          >
            {streamingContent}
            <span className="streaming-cursor" />
          </div>
        )}

        {/* Last response — full, not truncated */}
        {!isStreaming && lastAssistant && (
          <div
            className="text-xs leading-relaxed whitespace-pre-wrap break-words"
            style={{ color: 'var(--text-muted)' }}
          >
            {lastAssistant.content}
          </div>
        )}

        {/* Empty state */}
        {!isStreaming && !lastAssistant && (
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Ready to assist. Type below.
          </p>
        )}
      </div>
    </div>
  );
}
