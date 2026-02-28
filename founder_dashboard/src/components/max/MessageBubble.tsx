'use client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Message } from '@/lib/types';
import { ToolResultCard } from '@/components/desks/shared';
import { Copy, Check, Brain, Volume2, Square, Loader2 } from 'lucide-react';
import { useState, useRef, useCallback } from 'react';
import { API_URL } from '@/lib/api';

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-xs px-2 py-1 rounded"
      style={{ background: 'var(--elevated)', color: copied ? '#22c55e' : 'var(--text-secondary)', border: '1px solid var(--border)' }}
    >
      {copied ? <><Check className="w-3 h-3" />Copied</> : <><Copy className="w-3 h-3" />Copy</>}
    </button>
  );
}

function PlayButton({ text }: { text: string }) {
  const [state, setState] = useState<'idle' | 'loading' | 'playing'>('idle');
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
    }
    setState('idle');
  }, []);

  const play = useCallback(async () => {
    if (state === 'playing') { stop(); return; }

    // Strip markdown for cleaner speech
    const plain = text
      .replace(/```[\s\S]*?```/g, '')          // remove code blocks
      .replace(/`[^`]+`/g, '')                 // remove inline code
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // links → text only
      .replace(/[#*_~>|]/g, '')                // remove markdown chars
      .replace(/\n{2,}/g, '. ')                // paragraph breaks → periods
      .replace(/\n/g, ' ')                     // newlines → spaces
      .trim();

    if (!plain) return;

    setState('loading');
    try {
      const resp = await fetch(API_URL + '/max/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: plain }),
      });

      if (!resp.ok) { setState('idle'); return; }

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onplay = () => setState('playing');
      audio.onended = () => { URL.revokeObjectURL(url); audioRef.current = null; setState('idle'); };
      audio.onerror = () => { URL.revokeObjectURL(url); audioRef.current = null; setState('idle'); };

      await audio.play();
    } catch {
      setState('idle');
    }
  }, [text, state, stop]);

  const icon = state === 'loading'
    ? <Loader2 className="w-3 h-3 animate-spin" />
    : state === 'playing'
      ? <Square className="w-3 h-3" />
      : <Volume2 className="w-3 h-3" />;

  const label = state === 'loading' ? 'Loading...' : state === 'playing' ? 'Stop' : 'Listen';

  return (
    <button
      onClick={play}
      className="flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors"
      style={{
        background: state === 'playing' ? 'rgba(212,175,55,0.15)' : 'var(--elevated)',
        color: state === 'playing' ? 'var(--gold)' : 'var(--text-secondary)',
        border: `1px solid ${state === 'playing' ? 'var(--gold-border)' : 'var(--border)'}`,
      }}
      title={state === 'playing' ? 'Stop playback' : 'Listen to MAX'}
    >
      {icon}{label}
    </button>
  );
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={'msg-in flex ' + (isUser ? 'justify-end' : 'justify-start')}>
      {isUser ? (
        /* ── user bubble ───────────────────────────────────── */
        <div
          className="max-w-[78%] rounded-2xl rounded-br-sm px-4 py-3"
          style={{
            background: 'linear-gradient(135deg, #C9A025 0%, #D4AF37 60%, #B8962E 100%)',
            color: '#0a0a0a',
          }}
        >
          {message.image && (
            <p className="text-xs mb-2 opacity-60 flex items-center gap-1">📎 {message.image}</p>
          )}
          <p className="whitespace-pre-wrap text-sm leading-relaxed font-medium">{message.content}</p>
        </div>
      ) : (
        /* ── assistant bubble ─────────────────────────────── */
        <div className="max-w-[85%] flex gap-3 items-start">
          {/* MAX avatar beside bubble */}
          <div
            className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 mt-0.5 max-avatar-glow"
            style={{
              background: 'linear-gradient(135deg, #D4AF37 0%, #8B5CF6 100%)',
              border: '2px solid var(--gold)',
            }}
          >
            <Brain className="w-4 h-4 text-white" />
          </div>
        <div
          className="flex-1 rounded-2xl rounded-tl-sm px-4 py-3"
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
          }}
        >
          {message.image && (
            <p className="text-xs mb-2 flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>📎 {message.image}</p>
          )}
          <div className="chat-markdown">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const str   = String(children).replace(/\n$/, '');
                  const block = match || str.includes('\n');
                  return block ? (
                    <div className="relative group my-3">
                      <CopyButton text={str} />
                      <SyntaxHighlighter
                        style={oneDark}
                        language={match?.[1] || 'text'}
                        PreTag="div"
                        customStyle={{
                          background: '#0d0d1f',
                          borderRadius: '8px',
                          fontSize: '12.5px',
                          margin: 0,
                          border: '1px solid rgba(139,92,246,0.2)',
                        }}
                      >
                        {str}
                      </SyntaxHighlighter>
                    </div>
                  ) : (
                    <code
                      className="px-1.5 py-0.5 rounded text-xs font-mono"
                      style={{ background: 'var(--purple-pale)', color: '#c4b0ff', border: '1px solid var(--purple-border)' }}
                    >
                      {children}
                    </code>
                  );
                },
                table({ children }) {
                  return <div className="overflow-x-auto my-2"><table className="border-collapse w-full text-sm">{children}</table></div>;
                },
                th({ children }) {
                  return <th style={{ background: 'var(--elevated)', color: 'var(--gold)', borderColor: 'var(--border)' }} className="border px-3 py-1.5 text-left font-semibold">{children}</th>;
                },
                td({ children }) {
                  return <td style={{ borderColor: 'var(--border)' }} className="border px-3 py-1.5">{children}</td>;
                },
                a({ href, children }) {
                  return <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--purple)' }} className="underline hover:opacity-80">{children}</a>;
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
          {message.toolResults?.map((tr, i) => (
            <ToolResultCard key={i} result={tr} />
          ))}
          <div className="flex items-center gap-2 mt-2">
            <PlayButton text={message.content} />
            {message.model && (
              <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>via {message.model}</span>
            )}
          </div>
        </div>
        </div>
      )}
    </div>
  );
}
