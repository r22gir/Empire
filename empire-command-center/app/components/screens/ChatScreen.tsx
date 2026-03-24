'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Paperclip, Mic, MicOff, ArrowUp, Volume2, VolumeX, Mail, CheckSquare, Search, FileText, Calendar, ClipboardList, Loader2, Terminal, Headphones } from 'lucide-react';
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
  setOnMessageComplete?: (cb: ((msg: Message) => void) | null) => void;
}

export default function ChatScreen({ messages, isStreaming, streamingContent, streamingModel, onSend, onStop, onScreenChange, setOnMessageComplete }: Props) {
  const [input, setInput] = useState('');
  const [attachedImage, setAttachedImage] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const [codeMode, setCodeMode] = useState(false);
  const [codeModePin, setCodeModePin] = useState('');
  const [showPinModal, setShowPinModal] = useState(false);
  const [pinInput, setPinInput] = useState('');
  const [pinError, setPinError] = useState('');
  const [codeTask, setCodeTask] = useState<any>(null);
  const [voiceMode, setVoiceMode] = useState(false);
  const [ttsPlaying, setTtsPlaying] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const msgsEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const codePollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const voiceModeRef = useRef(false);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    msgsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, codeTask]);

  // Keep voiceMode ref in sync
  useEffect(() => { voiceModeRef.current = voiceMode; }, [voiceMode]);

  // Strip markdown for TTS (remove **, *, ```, tool blocks, links)
  const stripForTTS = (text: string) => {
    return text
      .replace(/```[\s\S]*?```/g, '')  // code blocks
      .replace(/\*\*(.*?)\*\*/g, '$1')  // bold
      .replace(/\*(.*?)\*/g, '$1')  // italic
      .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')  // links
      .replace(/#+\s/g, '')  // headings
      .replace(/\n{3,}/g, '\n\n')  // excess newlines
      .trim();
  };

  // Auto-play TTS when voice mode is on and AI responds
  const playTTSWithCallback = useCallback(async (text: string, onEnd?: () => void) => {
    const clean = stripForTTS(text);
    if (!clean || clean.length < 3) { onEnd?.(); return; }
    try {
      setTtsPlaying(true);
      const res = await fetch(API + '/max/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: clean.slice(0, 2000), voice: 'rex' }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        ttsAudioRef.current = audio;
        audio.onended = () => {
          setTtsPlaying(false);
          ttsAudioRef.current = null;
          URL.revokeObjectURL(url);
          onEnd?.();
        };
        audio.onerror = () => {
          setTtsPlaying(false);
          ttsAudioRef.current = null;
          onEnd?.();
        };
        audio.play();
      } else {
        setTtsPlaying(false);
        onEnd?.();
      }
    } catch {
      setTtsPlaying(false);
      onEnd?.();
    }
  }, []);

  // Start recording for voice mode (returns promise that resolves with transcript)
  const startVoiceCapture = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') return;
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
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
          if (data.text && voiceModeRef.current) {
            // In voice mode: auto-send the transcript
            onSend(data.text);
          } else if (data.text) {
            setInput(prev => prev + (prev ? ' ' : '') + data.text);
            textareaRef.current?.focus();
          }
        } catch (err) { console.warn('STT transcription failed:', err); }
        setRecording(false);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
    }).catch(() => { /* mic permission denied */ });
  }, [onSend]);

  // Register message complete callback for voice auto-play
  useEffect(() => {
    if (!setOnMessageComplete) return;
    if (voiceMode) {
      setOnMessageComplete((msg: Message) => {
        if (!voiceModeRef.current) return;
        // Auto-play TTS, then auto-listen
        playTTSWithCallback(msg.content, () => {
          if (voiceModeRef.current) {
            // Start listening again for continuous voice loop
            startVoiceCapture();
          }
        });
      });
    } else {
      setOnMessageComplete(null);
    }
    return () => { setOnMessageComplete?.(null); };
  }, [voiceMode, setOnMessageComplete, playTTSWithCallback, startVoiceCapture]);

  // Push-to-talk: spacebar (when textarea not focused)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !inputFocused && !e.repeat && document.activeElement?.tagName !== 'TEXTAREA' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        if (!recording) startVoiceCapture();
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space' && recording && !inputFocused && document.activeElement?.tagName !== 'TEXTAREA' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        mediaRecorderRef.current?.stop();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => { window.removeEventListener('keydown', handleKeyDown); window.removeEventListener('keyup', handleKeyUp); };
  }, [recording, inputFocused, startVoiceCapture]);

  // Stop TTS when voice mode turned off
  const toggleVoiceMode = useCallback(() => {
    setVoiceMode(prev => {
      const next = !prev;
      if (!next) {
        // Turning off — stop any playing TTS
        if (ttsAudioRef.current) {
          ttsAudioRef.current.pause();
          ttsAudioRef.current = null;
          setTtsPlaying(false);
        }
        // Stop recording if active
        if (mediaRecorderRef.current?.state === 'recording') {
          mediaRecorderRef.current.stop();
        }
      }
      return next;
    });
  }, []);

  // Poll code task status
  useEffect(() => {
    if (!codeTask || codeTask.state === 'completed' || codeTask.state === 'error') {
      if (codePollRef.current) { clearInterval(codePollRef.current); codePollRef.current = null; }
      return;
    }
    codePollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/max/code-task/${codeTask.id}/status`);
        if (r.ok) {
          const data = await r.json();
          setCodeTask(data);
          if (data.state === 'completed' || data.state === 'error') {
            if (codePollRef.current) clearInterval(codePollRef.current);
          }
        }
      } catch { /* offline */ }
    }, 2000);
    return () => { if (codePollRef.current) clearInterval(codePollRef.current); };
  }, [codeTask?.id, codeTask?.state]);

  const submitCodeTask = async (prompt: string) => {
    if (!codeModePin) {
      setShowPinModal(true);
      return;
    }
    try {
      const r = await fetch(`${API}/max/code-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, pin: codeModePin }),
      });
      if (r.ok) {
        const data = await r.json();
        setCodeTask({ id: data.task_id, state: data.state, prompt, log: [], files_changed: [] });
      } else if (r.status === 403) {
        setCodeModePin('');
        setCodeMode(false);
        setShowPinModal(true);
        setPinError('PIN expired or invalid. Please re-enter.');
      }
    } catch { /* offline */ }
  };

  const handlePinSubmit = async () => {
    setPinError('');
    try {
      const r = await fetch(`${API}/max/verify-pin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: pinInput }),
      });
      if (r.ok) {
        setCodeModePin(pinInput);
        setCodeMode(true);
        setShowPinModal(false);
        setPinInput('');
      } else {
        setPinError('Invalid PIN');
        setPinInput('');
      }
    } catch {
      setPinError('Connection error');
    }
  };

  const handleSend = () => {
    if (!input.trim() && !attachedImage) return;
    if (codeMode) {
      submitCodeTask(input.trim());
      setInput('');
      return;
    }
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
      return;
    }
    startVoiceCapture();
  }, [recording, startVoiceCapture]);

  const playTTS = async (text: string) => {
    playTTSWithCallback(text);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--chat-bg)' }}>

      {/* MAX Header — compact bold line */}
      <div style={{
        padding: '6px 0',
        textAlign: 'center',
        flexShrink: 0,
        borderBottom: '1px solid var(--border)',
        background: 'var(--card-bg)',
      }}>
        <span style={{
          fontSize: 14,
          fontWeight: 900,
          letterSpacing: 2,
          color: 'var(--text)',
          fontFamily: "'Inter', sans-serif",
        }}>
          MAX
        </span>
        {voiceMode && (
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            color: '#7c3aed',
            marginLeft: 10,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
          }}>
            <Headphones size={12} />
            {ttsPlaying ? 'Speaking...' : recording ? 'Listening...' : 'Voice Mode'}
            {' · '}
            <button
              onClick={toggleVoiceMode}
              style={{
                background: 'none', border: 'none', color: '#7c3aed',
                cursor: 'pointer', fontSize: 11, fontWeight: 600, textDecoration: 'underline',
                padding: 0,
              }}
            >
              Stop
            </button>
          </span>
        )}
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '8px 10px',
      }}
      className="sm:!px-9 sm:!py-6 pb-10 md:!pb-6">
        {messages.map((msg, i) => (
          <div key={msg.id || i} style={{
            marginBottom: 16,
            maxWidth: '90%',
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

        {/* Code Task progress card */}
        {codeTask && codeTask.state !== 'dismissed' && (
          <div style={{
            marginBottom: 16,
            maxWidth: '90%',
            borderRadius: 14,
            border: codeTask.state === 'error' ? '1.5px solid var(--red)' : '1.5px solid #b8960c',
            background: codeTask.state === 'error' ? '#fef2f2' : '#fffdf7',
            overflow: 'hidden',
          }}>
            {/* Header */}
            <div style={{
              padding: '10px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              borderBottom: '1px solid #f0e6c0',
              background: codeTask.state === 'error' ? '#fef2f2' : '#fdf8eb',
            }}>
              <Terminal size={14} style={{ color: codeTask.state === 'error' ? '#dc2626' : '#b8960c' }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: codeTask.state === 'error' ? '#dc2626' : '#b8960c', flex: 1 }}>
                Code Mode — {codeTask.state === 'queued' ? 'Queued' : codeTask.state === 'running' ? 'Atlas Working...' : codeTask.state === 'completed' ? 'Done' : 'Error'}
              </span>
              {(codeTask.state === 'running' || codeTask.state === 'queued') && (
                <Loader2 size={14} style={{ color: '#b8960c', animation: 'spin 1s linear infinite' }} />
              )}
              {(codeTask.state === 'completed' || codeTask.state === 'error') && (
                <button onClick={() => setCodeTask({ ...codeTask, state: 'dismissed' })} style={{
                  background: 'none', border: 'none', cursor: 'pointer', fontSize: 10, fontWeight: 600, color: '#999',
                }}>Dismiss</button>
              )}
            </div>

            {/* Prompt */}
            <div style={{ padding: '8px 16px', fontSize: 11, color: '#888', borderBottom: '1px solid #f5f0e0' }}>
              {codeTask.prompt?.slice(0, 120)}{codeTask.prompt?.length > 120 ? '...' : ''}
            </div>

            {/* Live log */}
            {codeTask.log?.length > 0 && (
              <div style={{ padding: '8px 16px', maxHeight: 120, overflowY: 'auto' }}>
                {codeTask.log.slice(-5).map((l: any, i: number) => (
                  <div key={i} style={{ fontSize: 10, color: '#666', display: 'flex', gap: 6, marginBottom: 3 }}>
                    <span style={{ color: '#b8960c', fontWeight: 700, textTransform: 'uppercase', fontSize: 9, minWidth: 50 }}>{l.action}</span>
                    <span>{l.detail}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Result */}
            {codeTask.state === 'completed' && codeTask.result && (
              <div style={{ padding: '10px 16px', fontSize: 13, color: '#333', lineHeight: 1.6, whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto', borderTop: '1px solid #f0e6c0' }}>
                {codeTask.result}
              </div>
            )}

            {/* Files changed */}
            {codeTask.state === 'completed' && codeTask.files_changed?.length > 0 && (
              <div style={{ padding: '8px 16px', borderTop: '1px solid #f0e6c0', display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {codeTask.files_changed.map((f: string, i: number) => (
                  <span key={i} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 6, background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#16a34a', fontFamily: 'monospace' }}>{f}</span>
                ))}
              </div>
            )}

            {/* Error */}
            {codeTask.state === 'error' && (
              <div style={{ padding: '10px 16px' }}>
                <div style={{ fontSize: 12, color: '#dc2626', marginBottom: 6 }}>{codeTask.error}</div>
                <button
                  onClick={() => { setCodeTask(null); submitCodeTask(codeTask.prompt); }}
                  style={{ fontSize: 11, fontWeight: 600, color: '#b8960c', background: 'none', border: '1px solid #b8960c', borderRadius: 8, padding: '4px 12px', cursor: 'pointer' }}
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        )}

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
      <div className="px-3 pt-2 pb-1 md:px-3 md:pt-3 md:pb-2" style={{
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

          {/* Voice Mode toggle */}
          <button
            onClick={toggleVoiceMode}
            title={voiceMode ? 'Voice Mode ON — auto-speak + auto-listen (click to disable)' : 'Voice Mode — hands-free conversation'}
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: voiceMode ? '#1a0a2e' : 'var(--card-bg)',
              border: voiceMode ? '1.5px solid #7c3aed' : '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: voiceMode ? '#7c3aed' : 'var(--dim)',
              flexShrink: 0,
              transition: 'all 0.2s',
              position: 'relative',
            }}
          >
            <Headphones size={17} />
            {voiceMode && (
              <span style={{
                position: 'absolute',
                top: -2,
                right: -2,
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: ttsPlaying ? '#7c3aed' : recording ? '#ef4444' : '#22c55e',
                animation: (ttsPlaying || recording) ? 'pulse 1.5s infinite' : 'none',
              }} />
            )}
          </button>

          {/* Code Mode toggle */}
          <button
            onClick={() => {
              if (codeMode) {
                setCodeMode(false);
                setCodeModePin('');
              } else if (codeModePin) {
                setCodeMode(true);
              } else {
                setPinInput('');
                setPinError('');
                setShowPinModal(true);
              }
            }}
            title={codeMode ? 'Code Mode ON — click to disable' : 'Code Mode — send to Atlas/Opus'}
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: codeMode ? '#1a1a1a' : 'var(--card-bg)',
              border: codeMode ? '1.5px solid #b8960c' : '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: codeMode ? '#b8960c' : 'var(--dim)',
              flexShrink: 0,
              transition: 'all 0.2s',
            }}
          >
            <Terminal size={17} />
          </button>

          {/* Text input */}
          <div style={{
            flex: 1,
            background: codeMode ? '#fdf8eb' : '#fff',
            border: `1.5px solid ${codeMode ? '#b8960c' : inputFocused ? 'var(--gold)' : 'var(--border)'}`,
            borderRadius: 14,
            transition: 'border-color 0.2s, box-shadow 0.2s, background 0.2s',
            boxShadow: codeMode ? '0 0 0 3px rgba(184,150,12,0.12)' : inputFocused ? '0 0 0 3px rgba(184,150,12,0.1)' : 'none',
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
              placeholder={codeMode ? 'Code Mode — describe what to build or fix...' : 'Message MAX...'}
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

        {/* Quick actions — hidden on mobile */}
        <div className="hidden md:flex" style={{
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

      {/* PIN Modal for Code Mode */}
      {showPinModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.6)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 20,
        }} onClick={() => setShowPinModal(false)}>
          <div style={{
            background: '#1a1a1a', borderRadius: 16, padding: 28, width: '100%', maxWidth: 340,
            border: '1.5px solid #b8960c', boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <Terminal size={20} style={{ color: '#b8960c' }} />
              <span style={{ color: '#fff', fontWeight: 700, fontSize: 16 }}>Code Mode — PIN Required</span>
            </div>
            <p style={{ color: '#aaa', fontSize: 13, marginBottom: 16, lineHeight: 1.4 }}>
              Code Mode grants Atlas (Opus) access to read and edit project files. Enter your founder PIN to activate.
            </p>
            {pinError && (
              <div style={{ color: '#ef4444', fontSize: 13, marginBottom: 12, fontWeight: 600 }}>{pinError}</div>
            )}
            <input
              type="password"
              inputMode="numeric"
              pattern="[0-9]*"
              value={pinInput}
              onChange={e => setPinInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handlePinSubmit(); }}
              placeholder="Enter PIN"
              autoFocus
              style={{
                width: '100%', padding: '14px 16px', fontSize: 18, fontWeight: 600,
                background: '#111', border: '1.5px solid #333', borderRadius: 12,
                color: '#fff', textAlign: 'center', letterSpacing: 8,
                outline: 'none', boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
              <button
                onClick={() => setShowPinModal(false)}
                style={{
                  flex: 1, padding: '12px 0', borderRadius: 10, border: '1px solid #333',
                  background: 'transparent', color: '#aaa', fontSize: 14, cursor: 'pointer',
                }}
              >Cancel</button>
              <button
                onClick={handlePinSubmit}
                style={{
                  flex: 1, padding: '12px 0', borderRadius: 10, border: 'none',
                  background: '#b8960c', color: '#000', fontSize: 14, fontWeight: 700,
                  cursor: 'pointer',
                }}
              >Activate</button>
            </div>
          </div>
        </div>
      )}

      {/* Animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
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
