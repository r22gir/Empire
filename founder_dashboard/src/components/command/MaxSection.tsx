'use client';
import { Message, AIModel } from '@/lib/types';
import { Brain, WifiOff } from 'lucide-react';
import ResponseCanvas from './ResponseCanvas';

interface Props {
  isStreaming: boolean;
  streamingContent: string;
  messages: Message[];
  backendOnline: boolean;
  selectedModel: string;
  models: AIModel[];
  onPresent?: (content: string) => void;
}

export default function MaxSection({ isStreaming, streamingContent, messages, backendOnline, selectedModel, models, onPresent }: Props) {
  const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant');
  const currentModel = models.find(m => m.id === selectedModel);
  const modelLabel = currentModel?.name || selectedModel;

  const statusColor = !backendOnline
    ? '#ef4444'
    : isStreaming ? 'var(--gold)' : '#22c55e';

  /* Determine what content to render */
  const displayContent = isStreaming
    ? streamingContent
    : lastAssistant?.content || '';

  return (
    <div className="flex flex-col min-h-0 flex-1">
      {/* Compact header — single line */}
      <div className="flex items-center gap-2 px-3 py-1.5 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="relative shrink-0">
          <div
            className={`w-6 h-6 rounded-full flex items-center justify-center ${
              isStreaming ? 'max-avatar-streaming' : 'max-avatar-glow'
            }`}
            style={{
              background: 'linear-gradient(135deg, #D4AF37 0%, #8B5CF6 100%)',
              border: '1px solid var(--gold)',
            }}
          >
            <Brain className="w-3 h-3 text-white" />
          </div>
          <div
            className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full"
            style={{
              background: statusColor,
              border: '1.5px solid var(--void)',
              animation: isStreaming ? 'pulse-online 1.5s infinite' : backendOnline ? 'pulse-online 2.2s infinite' : 'none',
            }}
          />
        </div>
        <span className="font-bold text-xs text-gold-shimmer tracking-wide">MAX</span>
        <span
          className="text-[8px] px-1 py-0.5 rounded-full font-mono"
          style={{ background: 'var(--purple-pale)', color: 'var(--purple)', border: '1px solid var(--purple-border)' }}
        >
          {modelLabel}
        </span>
        {isStreaming && (
          <span className="text-[9px]" style={{ color: 'var(--gold)' }}>
            {streamingContent ? 'speaking...' : 'thinking...'}
          </span>
        )}
        {isStreaming && !streamingContent && (
          <div className="typing-shimmer h-1.5 w-16 rounded-full" style={{ background: 'var(--elevated)' }} />
        )}
        {!backendOnline && <WifiOff className="w-3 h-3" style={{ color: '#ef4444' }} />}
      </div>

      {/* Response Canvas — fills all available space */}
      <ResponseCanvas content={displayContent} isStreaming={isStreaming} onPresent={onPresent} />
    </div>
  );
}
