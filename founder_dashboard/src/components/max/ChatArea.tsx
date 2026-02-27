'use client';
import { useRef, useEffect, useState } from 'react';
import { Message, AIModel as AIModelType } from '@/lib/types';
import MessageBubble from './MessageBubble';
import StreamingMessage from './StreamingMessage';
import ChatInput from './ChatInput';
import VoiceAgent from './VoiceAgent';
import { Brain, WifiOff, Mic } from 'lucide-react';

interface ChatAreaProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  selectedModel: string;
  models: AIModelType[];
  onSend: (input: string) => void;
  onStop: () => void;
  onOpenBrowser: () => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  uploading: boolean;
  pastedPreview: string | null;
  onUploadPasted: () => void;
  onCancelPasted: () => void;
  selectedImage: { name: string; category: string } | null;
  onClearImage: () => void;
  backendOnline: boolean;
}

export default function ChatArea(props: ChatAreaProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const [showVoice, setShowVoice] = useState(false);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [props.messages, props.streamingContent]);

  const currentModel = props.models.find(m => m.id === props.selectedModel);
  const modelLabel   = currentModel?.name || props.selectedModel;

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* ── Header ──────────────────────────────────────────── */}
      <div
        className="h-13 flex items-center justify-between px-5 shrink-0"
        style={{
          background:   'rgba(5,5,13,0.85)',
          borderBottom: '1px solid var(--border)',
          backdropFilter: 'blur(20px)',
          minHeight: '52px',
        }}
      >
        <div className="flex items-center gap-3">
          {/* MAX avatar */}
          <div
            className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
            style={{ background: 'linear-gradient(135deg, #D4AF37 0%, #8B5CF6 100%)' }}
          >
            <Brain className="w-4.5 h-4.5 text-white" style={{ width: '18px', height: '18px' }} />
          </div>
          <div>
            <span className="font-bold text-sm text-gold-shimmer tracking-wide">MAX</span>
            <span className="text-xs ml-2 font-light" style={{ color: 'var(--text-muted)' }}>Empire AI</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Voice button */}
          <button
            onClick={() => setShowVoice(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition"
            style={{
              background: 'var(--gold-pale)',
              color: 'var(--gold)',
              border: '1px solid var(--gold-border)',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--gold-active)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--gold-pale)'; }}
          >
            <Mic className="w-3.5 h-3.5" />
            Voice
          </button>

          {/* Model badge */}
          <span
            className="text-xs px-3 py-1.5 rounded-lg font-mono"
            style={{
              background: 'var(--purple-pale)',
              color:      'var(--purple)',
              border:     '1px solid var(--purple-border)',
            }}
          >
            {modelLabel}
          </span>
        </div>
      </div>

      {/* ── Offline banner ────────────────────────────────── */}
      {!props.backendOnline && (
        <div
          className="mx-4 mt-3 px-4 py-2.5 rounded-xl flex items-center gap-2.5 text-xs shrink-0"
          style={{
            background: 'rgba(212,175,55,0.06)',
            border:     '1px solid rgba(212,175,55,0.18)',
            color:      'rgba(212,175,55,0.75)',
          }}
        >
          <WifiOff className="w-3.5 h-3.5 shrink-0" />
          <span>
            Backend offline — start FastAPI on port&nbsp;
            <code
              className="px-1 rounded font-mono text-xs"
              style={{ background: 'rgba(212,175,55,0.1)', color: 'var(--gold)' }}
            >
              8000
            </code>
            &nbsp;for full AI chat.
          </span>
        </div>
      )}

      {/* ── Messages ──────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 min-h-0">
        {props.messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {props.isStreaming && <StreamingMessage content={props.streamingContent} />}
        <div ref={endRef} />
      </div>

      {/* ── Input ─────────────────────────────────────────── */}
      <ChatInput
        onSend={props.onSend}
        isStreaming={props.isStreaming}
        onStop={props.onStop}
        onOpenBrowser={props.onOpenBrowser}
        onFileUpload={props.onFileUpload}
        uploading={props.uploading}
        pastedPreview={props.pastedPreview}
        onUploadPasted={props.onUploadPasted}
        onCancelPasted={props.onCancelPasted}
        selectedImage={props.selectedImage}
        onClearImage={props.onClearImage}
      />

      {/* ── Voice Agent Modal ────────────────────────────── */}
      {showVoice && <VoiceAgent onClose={() => setShowVoice(false)} />}
    </div>
  );
}
