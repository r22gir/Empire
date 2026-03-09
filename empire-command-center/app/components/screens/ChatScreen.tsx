'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Paperclip, Mic, MicOff, ArrowUp, Volume2, Mail, CheckSquare, Search, FileText, Calendar, ClipboardList, Loader2 } from 'lucide-react';
import { Message } from '../../lib/types';
import { API } from '../../lib/api';
import QuoteCard from '../business/quotes/QuoteCard';

// Parse tool call blocks from message content: ```tool\n{...}\n``` or ```\n{"tool":...}\n```
function parseToolBlocks(content: string): { cleanContent: string; toolCalls: any[] } {
  const toolCalls: any[] = [];
  // Match ```tool ... ``` or ``` {"tool": ...} ```
  const cleaned = content.replace(/```(?:tool)?\s*\n?\s*(\{[\s\S]*?\})\s*\n?```/g, (_, json) => {
    try {
      const parsed = JSON.parse(json);
      if (parsed.tool) {
        toolCalls.push(parsed);
        return ''; // Remove from display
      }
    } catch { /* not valid JSON, leave as-is */ }
    return _;
  });
  return { cleanContent: cleaned.trim(), toolCalls };
}

// Check if content has a tool block being streamed (incomplete)
function hasStreamingToolBlock(content: string): boolean {
  // Detect an open ```tool block that hasn't closed yet
  const lastToolStart = content.lastIndexOf('```tool');
  const lastCodeStart = Math.max(content.lastIndexOf('```\n{"tool"'), content.lastIndexOf('```{"tool"'));
  const start = Math.max(lastToolStart, lastCodeStart);
  if (start === -1) return false;
  const afterStart = content.slice(start + 3);
  // Count closing ``` after the opening
  const closingMatch = afterStart.match(/```/);
  return !closingMatch;
}

const QUICK_ACTIONS = [
  { label: 'Quick Quote', icon: ClipboardList, action: 'quick-quote', highlight: true },
  { label: 'Mail', icon: Mail, action: 'briefing' },
  { label: 'Tasks', icon: CheckSquare, action: 'tasks' },
  { label: 'Research', icon: Search, action: 'research' },
  { label: 'Documents', icon: FileText, action: 'documents' },
  { label: 'Calendar', icon: Calendar, action: 'calendar' },
];

interface Props {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  streamingModel: string;
  onSend: (msg: string, imageFilename?: string | null) => void;
  onStop: () => void;
  onScreenChange?: (screen: string) => void;
}

export default function ChatScreen({ messages, isStreaming, streamingContent, streamingModel, onSend, onStop, onScreenChange }: Props) {
  const [input, setInput] = useState('');
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const msgsEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    msgsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSend = () => {
    if (!input.trim() && !attachedImage) return;
    onSend(input, attachedImage);
    setInput('');
    setAttachedImage(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'quick-quote':
        if (attachedImage) {
          onSend('Create a quick quote from this photo. Measure the window, suggest treatments, and generate a quote with pricing.', attachedImage);
          setAttachedImage(null);
        } else {
          // Prompt to attach image first, or just start quote flow
          onSend('I need to create a new quote. Help me start a quick quote — ask me for the customer name, room, and window details.');
        }
        break;
      case 'briefing': onScreenChange?.('inbox'); break;
      case 'tasks': onSend('Show my tasks for today'); break;
      case 'research': onScreenChange?.('research'); break;
      case 'documents': onScreenChange?.('docs'); break;
      case 'calendar': onSend('Show my calendar for today'); break;
      default: break;
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch(API + '/files/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.status === 'success') setAttachedImage(data.filename);
    } catch { /* silent */ }
  };

  const toggleRecording = useCallback(async () => {
    if (recording) {
      mediaRecorderRef.current?.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      const chunks: Blob[] = [];
      recorder.ondataavailable = e => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const fd = new FormData();
        fd.append('audio', blob, 'recording.webm');
        try {
          const res = await fetch(API.replace('/api/v1', '') + '/api/transcribe', { method: 'POST', body: fd });
          const data = await res.json();
          if (data.success && data.text) {
            setInput(prev => prev + (prev ? ' ' : '') + data.text);
            textareaRef.current?.focus();
          }
        } catch { /* silent */ }
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
    } catch { /* mic permission denied */ }
  }, [recording]);

  const playTTS = async (text: string) => {
    try {
      const res = await fetch(API + '/max/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 2000), voice: 'rex' }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        new Audio(url).play();
      }
    } catch { /* silent */ }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--chat-bg)' }}>

      {/* MAX Header */}
      <div style={{
        padding: '28px 36px 20px',
        textAlign: 'center',
        flexShrink: 0,
        borderBottom: '1px solid var(--border)',
        background: 'var(--card-bg)',
      }}>
        <h1 style={{
          fontSize: 26,
          fontWeight: 300,
          letterSpacing: 6,
          color: 'var(--text)',
          margin: 0,
          fontFamily: "'Inter', sans-serif",
        }}>
          M A X
        </h1>
        <p style={{
          fontSize: 13,
          color: '#aaa',
          marginTop: 4,
          fontWeight: 400,
        }}>
          Your empire. One voice.
        </p>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px 36px',
      }}>
        {messages.map((msg, i) => (
          <div key={msg.id || i} style={{
            marginBottom: 16,
            maxWidth: '75%',
            marginLeft: msg.role === 'user' ? 'auto' : undefined,
            marginRight: msg.role === 'user' ? 0 : 'auto',
          }}>
            {(() => {
              const { cleanContent, toolCalls } = msg.role === 'assistant'
                ? parseToolBlocks(msg.content)
                : { cleanContent: msg.content, toolCalls: [] };
              return (
                <>
                  {cleanContent && (
                    <div style={{
                      padding: '14px 18px',
                      fontSize: 14,
                      lineHeight: 1.65,
                      whiteSpace: 'pre-wrap',
                      ...(msg.role === 'user' ? {
                        background: 'var(--text)',
                        color: '#fff',
                        borderRadius: '14px 14px 6px 14px',
                      } : {
                        background: '#fff',
                        color: 'var(--text)',
                        border: '1px solid var(--border)',
                        borderRadius: '14px 14px 14px 6px',
                      }),
                    }}>
                      {renderContent(cleanContent, onScreenChange)}
                    </div>
                  )}
                  {/* Inline tool call cards (from message content) */}
                  {toolCalls.map((tc, k) => {
                    const isQuoteTool = tc.tool === 'create_quick_quote' || tc.tool === 'photo_to_quote';
                    if (isQuoteTool) {
                      return (
                        <div key={`tc-${k}`} style={{
                          marginTop: 10, padding: '14px 18px',
                          borderRadius: 14, border: '1.5px solid #f0e6c0',
                          background: '#fffdf7',
                        }}>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#b8960c', marginBottom: 4 }}>
                            Generating Quote...
                          </div>
                          <div style={{ fontSize: 13, color: '#555' }}>
                            {tc.customer_name && <span><strong>Customer:</strong> {tc.customer_name}</span>}
                            {tc.rooms?.[0]?.name && <span> · <strong>Room:</strong> {tc.rooms[0].name}</span>}
                            {tc.rooms?.[0]?.windows?.length && <span> · {tc.rooms[0].windows.length} window{tc.rooms[0].windows.length > 1 ? 's' : ''}</span>}
                          </div>
                          {tc.rooms?.[0]?.windows && (
                            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                              {tc.rooms[0].windows.slice(0, 6).map((w: any, wi: number) => (
                                <span key={wi} style={{
                                  fontSize: 10, padding: '3px 8px', borderRadius: 6,
                                  background: '#fdf8eb', border: '1px solid #f0e6c0', color: '#96750a',
                                }}>
                                  {w.name}: {w.width}&quot;×{w.height}&quot; · {w.treatmentType}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    }
                    // Generic tool call display
                    return (
                      <div key={`tc-${k}`} style={{
                        marginTop: 10, padding: '12px 16px', borderRadius: 14,
                        border: '1px solid var(--border)', background: '#faf9f7', fontSize: 12,
                      }}>
                        <strong style={{ color: '#555' }}>Tool: {tc.tool}</strong>
                      </div>
                    );
                  })}
                </>
              );
            })()}
            <div style={{
              fontSize: 10,
              color: 'var(--muted)',
              marginTop: 4,
              fontFamily: "'Inter', monospace",
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              ...(msg.role === 'user' ? { justifyContent: 'flex-end' } : {}),
            }} suppressHydrationWarning>
              {msg.timestamp}
              {msg.model && <span style={{ opacity: 0.7 }}>{msg.model}</span>}
              {msg.role === 'assistant' && msg.content.length > 20 && (
                <button
                  onClick={() => playTTS(msg.content)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--muted)',
                    cursor: 'pointer',
                    padding: 2,
                    display: 'inline-flex',
                    alignItems: 'center',
                    transition: 'color 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.color = 'var(--gold)')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'var(--muted)')}
                >
                  <Volume2 size={12} />
                </button>
              )}
            </div>
            {/* Tool results from SSE stream */}
            {msg.toolResults?.map((tr, j) => {
              if ((tr.tool === 'create_quick_quote' || tr.tool === 'photo_to_quote') && tr.success && tr.result) {
                return (
                  <QuoteCard
                    key={j}
                    result={tr.result}
                    onScreenChange={onScreenChange}
                    onSend={onSend}
                  />
                );
              }
              return null;
            })}
          </div>
        ))}

        {/* Streaming indicator */}
        {isStreaming && (
          <div style={{ marginBottom: 16, maxWidth: '75%' }}>
            <div style={{
              padding: '14px 18px',
              fontSize: 14,
              lineHeight: 1.65,
              whiteSpace: 'pre-wrap',
              background: '#fff',
              color: 'var(--text)',
              border: '1px solid var(--border)',
              borderRadius: '14px 14px 14px 6px',
            }}>
              {streamingContent || '...'}
            </div>
            <div style={{
              fontSize: 10,
              color: 'var(--muted)',
              marginTop: 4,
              fontFamily: "'Inter', monospace",
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              {streamingModel && <span>{streamingModel}</span>}
              <span style={{ opacity: 0.6 }}>typing...</span>
              <button
                onClick={onStop}
                style={{
                  marginLeft: 4,
                  color: 'var(--red)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 10,
                  fontWeight: 600,
                  padding: 0,
                }}
              >
                Stop
              </button>
            </div>
          </div>
        )}
        <div ref={msgsEndRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: '16px 36px 12px',
        flexShrink: 0,
        background: 'var(--chat-bg)',
      }}>
        <input ref={fileInputRef} type="file" style={{ display: 'none' }} accept="image/*" onChange={handleFileUpload} />

        {/* Attached image indicator */}
        {attachedImage && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: 'var(--gold-light)',
            border: '1px solid var(--gold)',
            borderRadius: 10,
            fontSize: 11,
            color: 'var(--gold)',
            fontWeight: 500,
            marginBottom: 10,
          }}>
            <Paperclip size={12} />
            {attachedImage}
            <button
              onClick={() => setAttachedImage(null)}
              style={{
                marginLeft: 4,
                fontWeight: 700,
                cursor: 'pointer',
                background: 'none',
                border: 'none',
                color: 'var(--gold)',
                fontSize: 13,
                lineHeight: 1,
              }}
            >
              x
            </button>
          </div>
        )}

        {/* Input row */}
        <div style={{
          display: 'flex',
          alignItems: 'flex-end',
          gap: 10,
        }}>
          {/* Attach button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: 'var(--card-bg)',
              border: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: 'var(--dim)',
              flexShrink: 0,
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = 'var(--border-h)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = 'var(--border)';
              e.currentTarget.style.transform = 'none';
            }}
          >
            <Paperclip size={17} />
          </button>

          {/* Mic button */}
          <button
            onClick={toggleRecording}
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: recording ? 'var(--red)' : 'var(--card-bg)',
              border: `1px solid ${recording ? 'var(--red)' : 'var(--border)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: recording ? '#fff' : 'var(--dim)',
              flexShrink: 0,
              transition: 'all 0.2s',
              animation: recording ? 'pulse 1.5s infinite' : 'none',
            }}
            onMouseEnter={e => {
              if (!recording) {
                e.currentTarget.style.borderColor = 'var(--border-h)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }
            }}
            onMouseLeave={e => {
              if (!recording) {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.transform = 'none';
              }
            }}
          >
            {recording ? <MicOff size={17} /> : <Mic size={17} />}
          </button>

          {/* Text input */}
          <div style={{
            flex: 1,
            background: '#fff',
            border: `1px solid ${inputFocused ? 'var(--gold)' : 'var(--border)'}`,
            borderRadius: 14,
            transition: 'border-color 0.2s, box-shadow 0.2s',
            boxShadow: inputFocused ? '0 0 0 3px rgba(184,150,12,0.1)' : 'none',
            display: 'flex',
            alignItems: 'flex-end',
          }}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
              placeholder="Message MAX..."
              rows={1}
              style={{
                flex: 1,
                padding: '13px 18px',
                border: 'none',
                outline: 'none',
                fontSize: 14,
                fontFamily: "'Inter', sans-serif",
                resize: 'none',
                minHeight: 44,
                maxHeight: 120,
                background: 'transparent',
                color: 'var(--text)',
                lineHeight: 1.5,
              }}
            />
          </div>

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={isStreaming}
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: 'var(--text)',
              border: 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: isStreaming ? 'not-allowed' : 'pointer',
              color: '#fff',
              flexShrink: 0,
              opacity: isStreaming ? 0.5 : 1,
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => {
              if (!isStreaming) e.currentTarget.style.background = 'var(--gold)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'var(--text)';
            }}
          >
            <ArrowUp size={20} />
          </button>
        </div>

        {/* Quick actions */}
        <div style={{
          display: 'flex',
          gap: 8,
          marginTop: 14,
          paddingBottom: 4,
          overflowX: 'auto',
        }}>
          {QUICK_ACTIONS.map(qa => {
            const Icon = qa.icon;
            const isHighlight = (qa as any).highlight;
            return (
              <button
                key={qa.action}
                onClick={() => handleQuickAction(qa.action)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 7,
                  padding: '8px 16px',
                  background: isHighlight ? '#fdf8eb' : '#fff',
                  border: isHighlight ? '1.5px solid #b8960c' : '1px solid var(--border)',
                  borderRadius: 12,
                  fontSize: 13,
                  fontWeight: isHighlight ? 700 : 500,
                  color: isHighlight ? '#b8960c' : 'var(--dim)',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.2s',
                  fontFamily: "'Inter', sans-serif",
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--gold)';
                  e.currentTarget.style.color = 'var(--gold)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(184,150,12,0.12)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = isHighlight ? '#b8960c' : 'var(--border)';
                  e.currentTarget.style.color = isHighlight ? '#b8960c' : 'var(--dim)';
                  e.currentTarget.style.transform = 'none';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <Icon size={15} />
                {qa.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Pulse animation for recording */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `}</style>
    </div>
  );
}

function renderContent(content: string, onScreenChange?: (s: string) => void) {
  return content.split('\n').map((line, i) => {
    // Bold
    let processed = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    processed = processed.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Detect QuoteBuilder / quote references and make them clickable
    const hasQuoteRef = /QuoteBuilder|quote.*interface/i.test(processed);
    if (hasQuoteRef && onScreenChange) {
      processed = processed.replace(
        /(QuoteBuilder\s*interface|QuoteBuilder)/gi,
        '<a class="quote-link" style="color:#b8960c;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:2px">$1</a>'
      );
    }
    // Detect quote numbers like EST-2026-027 and make clickable
    processed = processed.replace(
      /(EST-\d{4}-\d{3})/g,
      '<a class="quote-link" style="color:#b8960c;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:2px">$1</a>'
    );
    const html = processed + (i < content.split('\n').length - 1 ? '<br/>' : '');
    return (
      <span
        key={i}
        dangerouslySetInnerHTML={{ __html: html }}
        onClick={(e) => {
          const target = e.target as HTMLElement;
          if (target.classList.contains('quote-link')) {
            onScreenChange?.('quote');
          }
        }}
      />
    );
  });
}
