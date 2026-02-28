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

  const statusColor = !backendOnline
    ? '#ef4444'
    : isStreaming ? 'var(--gold)' : '#22c55e';

  useEffect(() => {
    if (isStreaming && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isStreaming, streamingContent]);

  return (
    <div className="flex flex-col min-h-0 flex-1">
      {/* Compact header — single line */}
      <div className="flex items-center gap-2.5 px-4 py-2 shrink-0">
        <div className="relative shrink-0">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center ${
              isStreaming ? 'max-avatar-streaming' : 'max-avatar-glow'
            }`}
            style={{
              background: 'linear-gradient(135deg, #D4AF37 0%, #8B5CF6 100%)',
              border: '1.5px solid var(--gold)',
            }}
          >
            <Brain className="w-4 h-4 text-white" />
          </div>
          <div
            className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full"
            style={{
              background: statusColor,
              border: '2px solid var(--void)',
              animation: isStreaming ? 'pulse-online 1.5s infinite' : backendOnline ? 'pulse-online 2.2s infinite' : 'none',
            }}
          />
        </div>
        <span className="font-bold text-sm text-gold-shimmer tracking-wide">MAX</span>
        <span
          className="text-[9px] px-1.5 py-0.5 rounded-full font-mono"
          style={{ background: 'var(--purple-pale)', color: 'var(--purple)', border: '1px solid var(--purple-border)' }}
        >
          {modelLabel}
        </span>
        {isStreaming && (
          <span className="text-[10px]" style={{ color: 'var(--gold)' }}>
            {streamingContent ? 'speaking...' : 'thinking...'}
          </span>
        )}
        {!backendOnline && <WifiOff className="w-3 h-3" style={{ color: '#ef4444' }} />}
      </div>

      {/* Response area — fills all available space */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 pb-2 min-h-0"
      >
        {isStreaming && !streamingContent && (
          <div className="typing-shimmer h-2 w-24 rounded-full mt-2" style={{ background: 'var(--elevated)' }} />
        )}

        {isStreaming && streamingContent && (
          <div
            className="text-sm leading-relaxed whitespace-pre-wrap break-words"
            style={{ color: 'var(--text-secondary)' }}
          >
            {streamingContent}
            <span className="streaming-cursor" />
          </div>
        )}

        {!isStreaming && lastAssistant && (
          <div
            className="text-sm leading-relaxed whitespace-pre-wrap break-words"
            style={{ color: 'var(--text-muted)' }}
          >
            {lastAssistant.content}
          </div>
        )}

        {!isStreaming && !lastAssistant && (
          <p className="text-sm pt-4 text-center" style={{ color: 'var(--text-muted)' }}>
            Ready. Type below to talk to MAX.
          </p>
        )}
      </div>
    </div>
  );
}
