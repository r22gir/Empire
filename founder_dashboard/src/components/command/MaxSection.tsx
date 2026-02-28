'use client';
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

  const statusText = !backendOnline
    ? 'Offline'
    : isStreaming
      ? streamingContent ? 'Speaking...' : 'Thinking...'
      : 'Online';

  const statusColor = !backendOnline
    ? '#ef4444'
    : isStreaming ? 'var(--gold)' : '#22c55e';

  return (
    <div
      className="rounded-2xl p-5"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <div className="flex items-start gap-4">
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

          <div className="flex items-center gap-2 mb-2">
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

          {/* Typing indicator */}
          {isStreaming && !streamingContent && (
            <div className="typing-shimmer h-2 w-24 rounded-full" style={{ background: 'var(--elevated)' }} />
          )}

          {/* Streaming preview */}
          {isStreaming && streamingContent && (
            <div
              className="text-xs leading-relaxed line-clamp-2 mt-1"
              style={{ color: 'var(--text-secondary)' }}
            >
              {streamingContent.slice(-150)}
              <span className="streaming-cursor" />
            </div>
          )}

          {/* Last response preview (when idle) */}
          {!isStreaming && lastAssistant && (
            <p
              className="text-xs leading-relaxed line-clamp-2 mt-1"
              style={{ color: 'var(--text-muted)' }}
            >
              {lastAssistant.content.slice(0, 150)}
              {lastAssistant.content.length > 150 && '...'}
            </p>
          )}

          {/* Empty state */}
          {!isStreaming && !lastAssistant && (
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
              Ready to assist. Type below or use voice.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
