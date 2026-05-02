'use client';
import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Paperclip, Mic, Send, Square, Code, Volume2,
  Trash2, Download, Image as ImageIcon, Sparkles,
  ChevronDown, X, AlertTriangle, CheckCircle, Clock, Shield
} from 'lucide-react';
import { Message } from '../../lib/types';
import { API } from '../../lib/api';

// Tool registry with safety metadata
interface ToolMeta {
  id: string;
  name: string;
  label: string;
  description: string;
  enabled: boolean;
  implemented: boolean;
  riskLevel: 'safe' | 'ai' | 'code' | 'financial' | 'deployment' | 'destructive' | 'unknown';
  requiresConfirmation: boolean;
}

const TOOL_REGISTRY: ToolMeta[] = [
  { id: 'code_task_runner', name: 'CodeTaskRunner', label: 'Code Task Runner', description: 'Run a code task via OpenClaw — may create/modify files', enabled: true, implemented: false, riskLevel: 'code', requiresConfirmation: true },
  { id: 'subdesk', name: 'SubDesk', label: 'Sub Desk', description: 'Route to a sub-desk for specialized tasks', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'vision_router', name: 'Vision Router', label: 'Vision Router', description: 'Route image analysis to the appropriate vision model', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'stt', name: 'STT', label: 'Speech to Text', description: 'Convert voice input to text', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'tts', name: 'TTS', label: 'Text to Speech', description: 'Convert AI response to voice output', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'inpaint', name: 'Inpaint', label: 'Inpaint', description: 'AI-powered image inpainting and editing', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'search', name: 'Search', label: 'Web Search', description: 'Search the web for information', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'extract', name: 'Extract', label: 'Extract Data', description: 'Extract structured data from unstructured input', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'translate', name: 'Translate', label: 'Translate', description: 'Translate text between languages', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'summarize', name: 'Summarize', label: 'Summarize', description: 'Summarize long content into key points', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'analyze', name: 'Analyze', label: 'Analyze', description: 'Analyze content and provide insights', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'classify', name: 'Classify', label: 'Classify', description: 'Classify content into categories', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'generate', name: 'Generate', label: 'Generate', description: 'Generate content or responses', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'format', name: 'Format', label: 'Format', description: 'Format and clean up content', enabled: true, implemented: false, riskLevel: 'ai', requiresConfirmation: false },
  { id: 'debug', name: 'Debug', label: 'Debug', description: 'Debug code and find errors', enabled: true, implemented: false, riskLevel: 'code', requiresConfirmation: true },
  { id: 'test', name: 'Test', label: 'Test', description: 'Run tests on code', enabled: true, implemented: false, riskLevel: 'code', requiresConfirmation: true },
  { id: 'deploy', name: 'Deploy', label: 'Deploy', description: 'Deploy application or configuration', enabled: true, implemented: false, riskLevel: 'deployment', requiresConfirmation: true },
  { id: 'monitor', name: 'Monitor', label: 'Monitor', description: 'Monitor system metrics and status', enabled: true, implemented: false, riskLevel: 'safe', requiresConfirmation: false },
  { id: 'backup', name: 'Backup', label: 'Backup', description: 'Create a backup of data or configuration', enabled: true, implemented: false, riskLevel: 'destructive', requiresConfirmation: true },
  { id: 'restore', name: 'Restore', label: 'Restore', description: 'Restore from a backup', enabled: true, implemented: false, riskLevel: 'destructive', requiresConfirmation: true },
];

type RiskLevel = ToolMeta['riskLevel'];

function RiskBadge({ risk }: { risk: RiskLevel }) {
  const config = {
    safe: { bg: 'rgba(22,163,74,0.15)', color: '#16a34a', label: 'Safe' },
    ai: { bg: 'rgba(99,102,241,0.15)', color: '#6366f1', label: 'AI' },
    code: { bg: 'rgba(234,179,8,0.15)', color: '#ca8a04', label: 'Code' },
    financial: { bg: 'rgba(239,68,68,0.15)', color: '#dc2626', label: 'Financial' },
    deployment: { bg: 'rgba(239,68,68,0.15)', color: '#dc2626', label: 'Deploy' },
    destructive: { bg: 'rgba(239,68,68,0.15)', color: '#dc2626', label: 'Dangerous' },
    unknown: { bg: 'rgba(255,255,255,0.05)', color: '#777', label: 'Unknown' },
  }[risk];
  return (
    <span style={{
      fontSize: 8, fontWeight: 700, padding: '1px 5px', borderRadius: 3,
      background: config.bg, color: config.color, textTransform: 'uppercase', letterSpacing: '0.5px',
    }}>
      {config.label}
    </span>
  );
}

function StatusBadge({ meta }: { meta: ToolMeta }) {
  if (!meta.implemented) {
    return <span style={{ fontSize: 9, color: '#777', display: 'flex', alignItems: 'center', gap: 2 }}><Clock size={9} /> Coming soon</span>;
  }
  if (meta.requiresConfirmation) {
    return <span style={{ fontSize: 9, color: '#ca8a04', display: 'flex', alignItems: 'center', gap: 2 }}><AlertTriangle size={9} /> Confirm</span>;
  }
  return <span style={{ fontSize: 9, color: '#16a34a', display: 'flex', alignItems: 'center', gap: 2 }}><CheckCircle size={9} /> Available</span>;
}

function ConfirmDialog({
  tool,
  onConfirm,
  onCancel,
}: {
  tool: ToolMeta;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 300,
      background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{
        background: 'rgba(30,41,59,0.98)', backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.15)',
        borderRadius: 16, padding: 24, maxWidth: 420, width: '90%',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <AlertTriangle size={18} style={{ color: '#ca8a04' }} />
          <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>
            Confirm: {tool.label}
          </span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 16 }}>
          {tool.description}<br/><br/>
          <span style={{ fontWeight: 600 }}>Risk level:</span> <RiskBadge risk={tool.riskLevel} /><br/>
          <span style={{ fontWeight: 600 }}>Branch:</span> feature/v10.0-test-lane (v10 test lane)<br/>
          <span style={{ fontWeight: 600 }}>Stable protected:</span> <span style={{ color: '#16a34a', fontWeight: 600 }}>Yes — no direct production deploy</span><br/><br/>
          <span style={{ color: '#ca8a04', fontWeight: 600 }}>Note:</span> Backend branch targeting is not yet enforced. This tool will run on whatever branch OpenClaw currently has active.
        </div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={{
            padding: '8px 16px', borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'rgba(255,255,255,0.06)', color: 'var(--text-muted)',
            cursor: 'pointer', fontSize: 12, fontWeight: 600,
          }}>
            Cancel
          </button>
          <button onClick={onConfirm} style={{
            padding: '8px 16px', borderRadius: 8,
            border: 'none',
            background: tool.riskLevel === 'destructive' || tool.riskLevel === 'deployment'
              ? '#dc2626' : 'var(--accent-primary)',
            color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 700,
          }}>
            Run {tool.label}
          </button>
        </div>
      </div>
    </div>
  );
}

interface ChatInterfaceProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  onSendMessage: (input: string, imageFile?: File) => void;
  onStopStreaming: () => void;
  onClearChat: () => void;
  codeMode: boolean;
  onToggleCodeMode: (enable: boolean) => void;
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
  const [toolsMenuOpen, setToolsMenuOpen] = useState(false);
  const [confirmTool, setConfirmTool] = useState<ToolMeta | null>(null);
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

  const handleToolClick = (toolId: string) => {
    const meta = TOOL_REGISTRY.find(t => t.id === toolId);
    if (!meta) return;
    if (!meta.implemented) return; // Coming soon — do nothing
    if (meta.requiresConfirmation) {
      setConfirmTool(meta);
      return;
    }
    // Safe: run directly
    executeTool(toolId);
  };

  const executeTool = async (toolId: string) => {
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

      {/* Tool bar — compact button + dropdown menu */}
      <div style={{
        padding: 'var(--space-2) var(--space-4)',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        gap: 'var(--space-2)',
        alignItems: 'center',
      }}>
        <button
          onClick={() => setToolsMenuOpen(v => !v)}
          title="Open tools menu"
          aria-label="Open tools menu"
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '5px 10px', borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(255,255,255,0.1)',
            background: toolsMenuOpen ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.06)',
            color: toolsMenuOpen ? 'var(--accent-primary)' : 'var(--text-muted)',
            cursor: 'pointer', fontSize: 'var(--text-xs)', fontWeight: 600,
          }}
        >
          <Sparkles size={12} /> Tools <ChevronDown size={10} />
        </button>
        {activeTool && (
          <span style={{ fontSize: 10, color: 'var(--accent-primary)', fontWeight: 600 }}>
            Running {TOOL_REGISTRY.find(t => t.id === activeTool)?.label || activeTool}...
          </span>
        )}
        {/* Inline tools menu */}
        {toolsMenuOpen && (
          <div style={{
            position: 'absolute', bottom: 'var(--space-4)',
            left: 'var(--space-4)',
            background: 'rgba(15,23,42,0.98)', backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: 12, padding: 12,
            width: 320, maxHeight: 400, overflowY: 'auto',
            zIndex: 100, boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '1px' }}>
                Tools
              </span>
              <button onClick={() => setToolsMenuOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 2 }}>
                <X size={14} />
              </button>
            </div>
            {TOOL_REGISTRY.map(tool => (
              <div key={tool.id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '6px 8px', borderRadius: 8,
                marginBottom: 2, cursor: tool.implemented ? 'pointer' : 'not-allowed',
                background: tool.implemented ? 'rgba(255,255,255,0.04)' : 'transparent',
                opacity: tool.implemented ? 1 : 0.5,
              }}
              onClick={() => {
                if (!tool.implemented) return;
                setToolsMenuOpen(false);
                handleToolClick(tool.id);
              }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{tool.label}</span>
                    <RiskBadge risk={tool.riskLevel} />
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>{tool.description}</div>
                </div>
                <StatusBadge meta={tool} />
              </div>
            ))}
          </div>
        )}
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
              minWidth: 0,
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
              onClick={() => { onToggleCodeMode(true); }}
              title="Enable Code Mode — opens confirmation dialog"
              aria-label="Enable Code Mode"
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

      {/* Tool Confirmation Dialog */}
      {confirmTool && (
        <ConfirmDialog
          tool={confirmTool}
          onConfirm={() => {
            executeTool(confirmTool.id);
            setConfirmTool(null);
          }}
          onCancel={() => setConfirmTool(null)}
        />
      )}
    </div>
  );
}
