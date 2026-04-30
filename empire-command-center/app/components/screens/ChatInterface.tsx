'use client';
import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Paperclip, Mic, Send, Square, Code, Volume2,
  Trash2, Download, Image as ImageIcon, Sparkles
} from 'lucide-react';
import { Message } from '../../lib/types';

const API = 'http://localhost:8000/api/v1';

interface Tool {
  id: string;
  name: string;
  icon: React.ReactNode;
}

const AVAILABLE_TOOLS: Tool[] = [
  { id: 'code_task_runner', name: 'CodeTaskRunner', icon: <Code size={14} /> },
  { id: 'subdesk', name: 'SubDesk', icon: <Sparkles size={14} /> },
  { id: 'vision_router', name: 'Vision Router', icon: <ImageIcon size={14} /> },
  { id: 'stt', name: 'STT', icon: <Mic size={14} /> },
  { id: 'tts', name: 'TTS', icon: <Volume2 size={14} /> },
  { id: 'inpaint', name: 'Inpaint', icon: <Sparkles size={14} /> },
  { id: 'search', name: 'Search', icon: <Sparkles size={14} /> },
  { id: 'extract', name: 'Extract', icon: <Sparkles size={14} /> },
  { id: 'translate', name: 'Translate', icon: <Sparkles size={14} /> },
  { id: 'summarize', name: 'Summarize', icon: <Sparkles size={14} /> },
  { id: 'analyze', name: 'Analyze', icon: <Sparkles size={14} /> },
  { id: 'classify', name: 'Classify', icon: <Sparkles size={14} /> },
  { id: 'generate', name: 'Generate', icon: <Sparkles size={14} /> },
  { id: 'format', name: 'Format', icon: <Sparkles size={14} /> },
  { id: 'debug', name: 'Debug', icon: <Code size={14} /> },
  { id: 'test', name: 'Test', icon: <Sparkles size={14} /> },
  { id: 'deploy', name: 'Deploy', icon: <Sparkles size={14} /> },
  { id: 'monitor', name: 'Monitor', icon: <Sparkles size={14} /> },
  { id: 'backup', name: 'Backup', icon: <Sparkles size={14} /> },
  { id: 'restore', name: 'Restore', icon: <Sparkles size={14} /> },
];

interface ChatInterfaceProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  onSendMessage: (input: string, imageFile?: File) => void;
  onStopStreaming: () => void;
  onClearChat: () => void;
  codeMode: boolean;
  onToggleCodeMode: () => void;
  voiceMode: boolean;
  onToggleVoiceMode: () => void;
  activeDesk: string;
}

function parseMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background:rgba(99,102,241,0.15);padding:2px 6px;border-radius:4px;font-family:var(--font-mono);font-size:0.85em;">$1</code>')
    .replace(/```(\w+)?\n([\s\S]+?)```/g, '<pre style="background:rgba(30,41,59,0.9);padding:var(--space-3);border-radius:var(--radius-md);overflow-x:auto;margin:8px 0;"><code>$2</code></pre>')
    .replace(/\n/g, '<br/>');
}

export function ChatInterface({
  messages,
  isStreaming,
  streamingContent,
  onSendMessage,
  onStopStreaming,
  onClearChat,
  codeMode,
  onToggleCodeMode,
  voiceMode,
  onToggleVoiceMode,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input, selectedImage || undefined);
    setInput('');
    setSelectedImage(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleToolClick = async (toolId: string) => {
    setActiveTool(toolId);
    try {
      await fetch(`${API}/max/tools/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: toolId }),
      });
    } catch { /* silent */ }
    setTimeout(() => setActiveTool(null), 2000);
  };

  const handleExportChat = () => {
    const content = messages.map(m =>
      `[${m.timestamp}] ${m.role === 'user' ? 'You' : 'MAX'}: ${m.content}`
    ).join('\n\n');
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `max-chat-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'var(--bg-primary)',
    }}>
      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: 'var(--space-4)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-4)',
      }}>
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                justifyContent: isUser ? 'flex-end' : 'flex-start',
                alignItems: 'flex-start',
                gap: 'var(--space-3)',
              }}
            >
              {!isUser && (
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--accent-gradient)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <Sparkles size={14} color="#fff" />
                </div>
              )}
              <div suppressHydrationWarning style={{

                maxWidth: isUser ? "75%" : "85%",
                background: isUser
                  ? 'var(--accent-primary)'
                  : 'rgba(30,41,59,0.72)',
                backdropFilter: 'blur(18px)',
                border: isUser
                  ? 'none'
                  : '1px solid rgba(255,255,255,0.12)',
                borderRadius: isUser
                  ? 'var(--radius-2xl)'
                  : 'var(--radius-lg)',
                padding: 'var(--space-3) var(--space-4)',
                boxShadow: isUser
                  ? '0 4px 16px rgba(99,102,241,0.3)'
                  : '0 4px 16px rgba(0,0,0,0.3)',
              }}>
                <div
                  style={{
                    color: isUser ? '#fff' : 'var(--text-primary)',
                    fontSize: 'var(--text-sm)',
                    lineHeight: 1.6,
                  }}
                  dangerouslySetInnerHTML={{ __html: parseMarkdown(msg.content) }}
                />
                {msg.toolResults && msg.toolResults.length > 0 && (
                  <div style={{
                    marginTop: 'var(--space-2)',
                    paddingTop: 'var(--space-2)',
                    borderTop: '1px solid rgba(255,255,255,0.1)',
                  }}>
                    {msg.toolResults.map((tr, i) => (
                      <div key={i} style={{
                        fontSize: 'var(--text-xs)',
                        color: tr.success ? 'var(--success)' : 'var(--error)',
                        fontFamily: 'var(--font-mono)',
                      }}>
                        {tr.success ? '✓' : '✗'} {tr.tool}
                      </div>
                    ))}
                  </div>
                )}
                <div style={{
                  marginTop: 'var(--space-2)',
                  fontSize: 'var(--text-xs)',
                  color: isUser ? 'rgba(255,255,255,0.6)' : 'var(--text-muted)',
                  display: 'flex',
                  gap: 'var(--space-3)',
                }}>
                  <span>{msg.timestamp}</span>
                  {msg.model && <span>{msg.model}</span>}
                  {msg.latency && <span>{msg.latency}</span>}
                </div>
              </div>
              {isUser && (
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: 'var(--radius-full)',
                  background: 'rgba(99,102,241,0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <span style={{ color: '#fff', fontSize: 'var(--text-xs)', fontWeight: 700 }}>Y</span>
                </div>
              )}
            </div>
          );
        })}

        {/* Streaming indicator */}
        {isStreaming && streamingContent && (
          <div style={{
            display: 'flex',
            justifyContent: 'flex-start',
            alignItems: 'flex-start',
            gap: 'var(--space-3)',
          }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 'var(--radius-full)',
              background: 'var(--accent-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Sparkles size={14} color="#fff" />
            </div>
            <div style={{
              maxWidth: '85%',
              background: 'rgba(30,41,59,0.72)',
              backdropFilter: 'blur(18px)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-3) var(--space-4)',
            }}>
              <div style={{
                color: 'var(--text-primary)',
                fontSize: 'var(--text-sm)',
                lineHeight: 1.6,
              }}>
                <span dangerouslySetInnerHTML={{ __html: parseMarkdown(streamingContent) }} />
                <span style={{
                  display: 'inline-block',
                  width: 6,
                  height: 14,
                  background: 'var(--accent-primary)',
                  marginLeft: 4,
                  borderRadius: 2,
                  animation: 'blink 1s infinite',
                }} />
              </div>
            </div>
          </div>
        )}

        {/* Typing indicator */}
        {isStreaming && !streamingContent && (
          <div style={{
            display: 'flex',
            justifyContent: 'flex-start',
            alignItems: 'flex-start',
            gap: 'var(--space-3)',
          }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 'var(--radius-full)',
              background: 'var(--accent-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Sparkles size={14} color="#fff" />
            </div>
            <div style={{
              background: 'rgba(30,41,59,0.72)',
              backdropFilter: 'blur(18px)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-3) var(--space-4)',
            }}>
              <div style={{ display: 'flex', gap: 4 }}>
                {[0, 1, 2].map((i) => (
                  <div key={i} style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: 'var(--accent-primary)',
                    animation: `bounce 1.2s infinite`,
                    animationDelay: `${i * 0.15}s`,
                  }} />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Tool bar */}
      <div style={{
        padding: 'var(--space-2) var(--space-4)',
        borderTop: '1px solid var(--border-subtle)',
        overflowX: 'auto',
        display: 'flex',
        gap: 'var(--space-2)',
        scrollbarWidth: 'thin',
      }}>
        {AVAILABLE_TOOLS.map((tool) => (
          <button
            key={tool.id}
            onClick={() => handleToolClick(tool.id)}
            title={`Run ${tool.name}`}
            aria-label={`Run ${tool.name}`}
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-full)',
              background: activeTool === tool.id
                ? 'var(--accent-primary)'
                : 'rgba(255,255,255,0.06)',
              border: activeTool === tool.id
                ? '1px solid var(--accent-primary)'
                : '1px solid rgba(255,255,255,0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              color: activeTool === tool.id ? '#fff' : 'var(--text-muted)',
              boxShadow: activeTool === tool.id
                ? '0 0 20px rgba(99,102,241,0.4)'
                : 'none',
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              if (activeTool !== tool.id) {
                e.currentTarget.style.transform = 'scale(1.1)';
                e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
              }
            }}
            onMouseLeave={(e) => {
              if (activeTool !== tool.id) {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
              }
            }}
          >
            {tool.icon}
          </button>
        ))}
      </div>

      {/* Input area */}
      <div style={{
        padding: 'var(--space-4)',
        borderTop: '1px solid var(--border-subtle)',
      }}>
        {selectedImage && (
          <div style={{
            marginBottom: 'var(--space-2)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
            padding: 'var(--space-2)',
            background: 'rgba(99,102,241,0.1)',
            borderRadius: 'var(--radius-md)',
          }}>
            <ImageIcon size={14} style={{ color: 'var(--accent-primary)' }} />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
              {selectedImage.name}
            </span>
            <button
              onClick={() => setSelectedImage(null)}
              style={{
                marginLeft: 'auto',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
              }}
            >
              ×
            </button>
          </div>
        )}
        <div style={{
          display: 'flex',
          gap: 'var(--space-2)',
          background: 'rgba(30,41,59,0.7)',
          backdropFilter: 'blur(18px)',
          border: '1px solid rgba(255,255,255,0.12)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-2) var(--space-3)',
          alignItems: 'flex-end',
        }}>
          <input
            type="file"
            ref={fileInputRef}
            accept="image/*"
            onChange={(e) => setSelectedImage(e.target.files?.[0] || null)}
            style={{ display: 'none' }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            title="Attach image"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              transition: 'color 0.2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; }}
          >
            <Paperclip size={18} />
          </button>
          <button
            onClick={() => {}}
            title="Voice input — coming soon"
            aria-label="Voice input (not available yet)"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'not-allowed',
              padding: '4px',
              display: 'flex',
              transition: 'color 0.2s',
              opacity: 0.4,
            }}
          >
            <Mic size={18} />
          </button>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message MAX..."
            rows={1}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              fontSize: 'var(--text-sm)',
              fontFamily: 'var(--font-sans)',
              resize: 'none',
              outline: 'none',
              lineHeight: 1.5,
              maxHeight: '120px',
              overflowY: 'auto',
            }}
          />
          <div style={{ display: 'flex', gap: 'var(--space-1)', alignItems: 'center' }}>
            <button
              onClick={onToggleCodeMode}
              title={codeMode ? 'Disable Code Mode' : 'Enable Code Mode'}
              style={{
                background: codeMode ? 'var(--accent-primary)' : 'transparent',
                border: 'none',
                color: codeMode ? '#fff' : 'var(--text-muted)',
                cursor: 'pointer',
                padding: '4px',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                transition: 'all 0.2s',
              }}
            >
              <Code size={16} />
            </button>
            <button
              onClick={() => {}}
              title="Voice mode — coming soon"
              aria-label="Voice mode (not available yet)"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'not-allowed',
                padding: '4px',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                transition: 'all 0.2s',
                opacity: 0.4,
              }}
            >
              <Volume2 size={16} />
            </button>
            <button
              onClick={onClearChat}
              title="Clear chat"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                transition: 'color 0.2s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--error)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; }}
            >
              <Trash2 size={16} />
            </button>
            <button
              onClick={handleExportChat}
              title="Export chat"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                transition: 'color 0.2s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--text-primary)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; }}
            >
              <Download size={16} />
            </button>
            {isStreaming ? (
              <button
                onClick={onStopStreaming}
                title="Stop"
                style={{
                  background: 'var(--error)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  color: '#fff',
                  cursor: 'pointer',
                  padding: '6px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-1)',
                }}
              >
                <Square size={14} /> Stop
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!input.trim()}
                title="Send message"
                style={{
                  background: input.trim() ? 'var(--accent-primary)' : 'rgba(99,102,241,0.3)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  color: '#fff',
                  cursor: input.trim() ? 'pointer' : 'not-allowed',
                  padding: '6px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  transition: 'all 0.2s',
                }}
              >
                <Send size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  );
}
