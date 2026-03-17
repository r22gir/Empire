'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Mic, MicOff, Send, Monitor, Square, MessageSquare, Sparkles, Wifi, WifiOff } from 'lucide-react';

const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1');

type PresentationMode = 'presentation' | 'compact' | 'text';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  desk?: string;
  model?: string;
  hasAudio?: boolean;
}

// ── TalkingHead Avatar Component (iframe-loaded) ────────────────────────
function AvatarPanel({ mode, isSpeaking, isThinking, iframeRef }: { mode: PresentationMode; isSpeaking: boolean; isThinking: boolean; iframeRef: React.RefObject<HTMLIFrameElement | null> }) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Listen for messages from avatar iframe
  useEffect(() => {
    if (mode !== 'presentation') return;

    const handler = (event: MessageEvent) => {
      if (event.data?.type === 'avatar-loaded') {
        if (event.data.success) {
          setLoaded(true);
          setError(null);
        } else {
          setError('placeholder');
        }
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [mode]);

  if (mode !== 'presentation') return null;

  return (
    <div
      className="w-full h-[200px] md:w-[60%] md:h-auto"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(180deg, #1a1812 0%, #0d0b08 100%)',
        borderRight: '2px solid #b8960c',
        position: 'relative',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Empire branding */}
      <div style={{
        position: 'absolute', top: 16, left: 20,
        display: 'flex', alignItems: 'center', gap: 8, zIndex: 10,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: 'linear-gradient(135deg, #b8960c, #d4af37)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Sparkles size={16} color="#fff" />
        </div>
        <span style={{ color: '#d4af37', fontWeight: 700, fontSize: 14, letterSpacing: 1 }}>
          MAX — Empire AI
        </span>
      </div>

      {/* Gold glow border effect */}
      <div style={{
        position: 'absolute', inset: 0,
        border: '2px solid rgba(184, 150, 12, 0.3)',
        borderRadius: 0,
        boxShadow: 'inset 0 0 60px rgba(184, 150, 12, 0.05)',
        pointerEvents: 'none',
      }} />

      {/* Avatar canvas or placeholder */}
      {error === 'placeholder' ? (
        <div style={{
          width: 280, height: 360,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 16,
        }}>
          <div style={{
            width: 160, height: 160, borderRadius: '50%',
            background: 'linear-gradient(135deg, #b8960c 0%, #d4af37 50%, #f0d060 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: isSpeaking
              ? '0 0 40px rgba(184,150,12,0.6), 0 0 80px rgba(184,150,12,0.3)'
              : isThinking
              ? '0 0 30px rgba(139,92,246,0.4)'
              : '0 0 20px rgba(184,150,12,0.2)',
            transition: 'box-shadow 0.3s ease',
            animation: isSpeaking ? 'pulse-avatar 1s ease-in-out infinite' : isThinking ? 'pulse-think 1.5s ease-in-out infinite' : 'none',
          }}>
            <Sparkles size={64} color="#fff" style={{
              animation: isSpeaking ? 'sparkle-spin 2s linear infinite' : 'none',
            }} />
          </div>
          <span style={{ color: '#d4af37', fontSize: 20, fontWeight: 700, letterSpacing: 2 }}>MAX</span>
          {isThinking && (
            <div style={{ display: 'flex', gap: 6 }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: '#b8960c',
                  animation: `dot-bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                }} />
              ))}
            </div>
          )}
          {isSpeaking && (
            <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 24 }}>
              {[0, 1, 2, 3, 4].map(i => (
                <div key={i} style={{
                  width: 4, borderRadius: 2,
                  background: '#d4af37',
                  animation: `speak-bar 0.6s ease-in-out ${i * 0.1}s infinite`,
                }} />
              ))}
            </div>
          )}
        </div>
      ) : (
        <iframe
          ref={iframeRef}
          src="/avatar.html"
          style={{
            width: '100%', height: '100%',
            border: 'none',
            opacity: loaded ? 1 : 0.3,
            transition: 'opacity 0.5s ease',
            background: 'transparent',
          }}
          allow="autoplay"
        />
      )}

      {!loaded && !error && (
        <div style={{
          position: 'absolute', bottom: 20,
          color: '#b8960c', fontSize: 12, opacity: 0.6,
        }}>
          Loading avatar...
        </div>
      )}

      <style>{`
        @keyframes pulse-avatar {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.03); }
        }
        @keyframes pulse-think {
          0%, 100% { transform: scale(1); opacity: 0.8; }
          50% { transform: scale(1.02); opacity: 1; }
        }
        @keyframes sparkle-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes dot-bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-8px); opacity: 1; }
        }
        @keyframes speak-bar {
          0%, 100% { height: 4px; }
          50% { height: 20px; }
        }
      `}</style>
    </div>
  );
}

// ── Mini Avatar (Compact Mode) ───────────────────────────────────────
function MiniAvatar({ onClick, isSpeaking, isThinking }: { onClick: () => void; isSpeaking: boolean; isThinking: boolean }) {
  return (
    <button
      onClick={onClick}
      style={{
        position: 'fixed', bottom: 20, left: 20, zIndex: 50,
        width: 64, height: 64, borderRadius: '50%',
        background: 'linear-gradient(135deg, #b8960c, #d4af37)',
        border: '2px solid rgba(184,150,12,0.5)',
        cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: isSpeaking
          ? '0 0 20px rgba(184,150,12,0.5)'
          : '0 4px 12px rgba(0,0,0,0.15)',
        transition: 'all 0.2s ease',
        animation: isThinking ? 'pulse-think 1.5s ease-in-out infinite' : 'none',
      }}
      title="Expand to Presentation mode"
    >
      <Sparkles size={28} color="#fff" />
    </button>
  );
}

// ── Mode Toggle ──────────────────────────────────────────────────────
function ModeToggle({ mode, onChange }: { mode: PresentationMode; onChange: (m: PresentationMode) => void }) {
  const modes: { id: PresentationMode; label: string; icon: React.ReactNode; dot?: string }[] = [
    { id: 'presentation', label: 'Presentation', icon: <Monitor size={14} />, dot: '#b8960c' },
    { id: 'compact', label: 'Compact', icon: <Square size={14} />, dot: '#9ca3af' },
    { id: 'text', label: 'Text', icon: <MessageSquare size={14} /> },
  ];

  return (
    <div style={{
      display: 'flex', gap: 4, background: '#f5f3ef',
      borderRadius: 10, padding: 3,
    }}>
      {modes.map(m => (
        <button
          key={m.id}
          onClick={() => onChange(m.id)}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '6px 12px', borderRadius: 8,
            fontSize: 11, fontWeight: mode === m.id ? 600 : 400,
            background: mode === m.id ? '#fff' : 'transparent',
            border: mode === m.id ? '1px solid #e5e2dc' : '1px solid transparent',
            boxShadow: mode === m.id ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
            color: mode === m.id ? '#1a1a1a' : '#999',
            cursor: 'pointer',
            minHeight: 32,
            transition: 'all 0.15s ease',
          }}
          title={`${m.label} mode${m.id === 'presentation' ? ' (Ctrl+Shift+P)' : ''}`}
        >
          {m.dot && <span style={{ width: 6, height: 6, borderRadius: '50%', background: m.dot }} />}
          {m.icon}
          {m.label}
        </button>
      ))}
    </div>
  );
}

// ── Main PresentationScreen ──────────────────────────────────────────
export default function PresentationScreen() {
  const [mode, setMode] = useState<PresentationMode>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('empire-presentation-mode') as PresentationMode) || 'text';
    }
    return 'text';
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [sessionCost, setSessionCost] = useState(0);
  const [connected, setConnected] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Persist mode
  useEffect(() => {
    localStorage.setItem('empire-presentation-mode', mode);
  }, [mode]);

  // Keyboard shortcut: Ctrl+Shift+P cycles modes
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'P') {
        e.preventDefault();
        setMode(prev => {
          const cycle: PresentationMode[] = ['text', 'compact', 'presentation'];
          const idx = cycle.indexOf(prev);
          return cycle[(idx + 1) % cycle.length];
        });
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Check backend connectivity
  useEffect(() => {
    const check = async () => {
      try {
        const resp = await fetch(`${API}/avatar/status`, { signal: AbortSignal.timeout(3000) });
        setConnected(resp.ok);
      } catch { setConnected(false); }
    };
    check();
    const iv = setInterval(check, 15000);
    return () => clearInterval(iv);
  }, []);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleModeChange = useCallback((newMode: PresentationMode) => {
    setMode(newMode);
    // Stop any playing audio when switching away from presentation
    if (newMode !== 'presentation' && audioRef.current) {
      audioRef.current.pause();
      setIsSpeaking(false);
    }
  }, []);

  const playAudio = useCallback((audioB64: string) => {
    if (!audioB64) return;
    const audio = new Audio(`data:audio/mp3;base64,${audioB64}`);
    audioRef.current = audio;
    setIsSpeaking(true);
    audio.onended = () => setIsSpeaking(false);
    audio.onerror = () => setIsSpeaking(false);
    audio.play().catch(() => setIsSpeaking(false));
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const resp = await fetch(`${API}/avatar/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text.trim(),
          voice: mode === 'presentation',
          mode,
        }),
      });
      const data = await resp.json();

      const assistMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || data.detail || 'No response',
        timestamp: new Date().toISOString(),
        desk: data.desk,
        model: data.model_used,
        hasAudio: !!data.audio,
      };
      setMessages(prev => [...prev, assistMsg]);

      // Play audio in presentation mode + lip-sync avatar
      if (mode === 'presentation') {
        if (data.audio) {
          playAudio(data.audio);
          // Send audio to avatar for lip-sync
          iframeRef.current?.contentWindow?.postMessage(
            { type: 'speak-audio', audio: data.audio }, '*'
          );
          setSessionCost(prev => prev + 0.015); // ~$0.015 per TTS call
        } else if (assistMsg.content) {
          // No audio — use TalkingHead's built-in TTS for lip-sync
          iframeRef.current?.contentWindow?.postMessage(
            { type: 'speak-text', text: assistMsg.content }, '*'
          );
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Connection error: ${err instanceof Error ? err.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setIsLoading(false);
    }
  }, [mode, isLoading, playAudio]);

  // Voice recording — Web Speech API primary (mobile), MediaRecorder fallback (desktop)
  const toggleRecording = useCallback(async () => {
    if (isRecording) {
      if ((window as any).__speechRecognition) {
        (window as any).__speechRecognition.stop();
      } else {
        mediaRecorderRef.current?.stop();
      }
      setIsRecording(false);
      return;
    }

    // Try Web Speech API first (works reliably on mobile)
    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        (window as any).__speechRecognition = recognition;

        recognition.onresult = async (event: any) => {
          const transcript = event.results[0][0].transcript;
          setIsRecording(false);
          (window as any).__speechRecognition = null;
          if (!transcript) return;

          // Add user message
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: 'user',
            content: transcript,
            timestamp: new Date().toISOString(),
          }]);

          // Send to MAX via avatar/chat (text, not audio)
          setIsLoading(true);
          try {
            const resp = await fetch(`${API}/avatar/chat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: transcript, voice: mode === 'presentation', channel: 'avatar', mode }),
            });
            const data = await resp.json();
            if (data.response) {
              setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: data.response,
                timestamp: new Date().toISOString(),
                model: data.model_used,
                hasAudio: !!data.audio,
              }]);
              if (mode === 'presentation') {
                if (data.audio) {
                  playAudio(data.audio);
                  iframeRef.current?.contentWindow?.postMessage(
                    { type: 'speak-audio', audio: data.audio }, '*'
                  );
                  setSessionCost(prev => prev + 0.015);
                } else if (data.response) {
                  iframeRef.current?.contentWindow?.postMessage(
                    { type: 'speak-text', text: data.response }, '*'
                  );
                }
              }
            }
          } catch (e) {
            console.error('Chat failed:', e);
          } finally {
            setIsLoading(false);
          }
        };

        recognition.onerror = (event: any) => {
          console.error('Speech recognition error:', event.error);
          setIsRecording(false);
          (window as any).__speechRecognition = null;
        };

        recognition.onend = () => {
          setIsRecording(false);
          (window as any).__speechRecognition = null;
        };

        recognition.start();
        setIsRecording(true);
        return;
      } catch (e) {
        console.error('SpeechRecognition failed, falling back to MediaRecorder:', e);
      }
    }

    // Fallback: MediaRecorder (desktop)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunks, { type: recorder.mimeType });
        const formData = new FormData();
        formData.append('file', blob, recorder.mimeType.includes('mp4') ? 'voice.mp4' : 'voice.webm');
        formData.append('mode', mode);

        setIsLoading(true);
        try {
          const resp = await fetch(`${API}/avatar/listen`, {
            method: 'POST',
            body: formData,
          });
          const data = await resp.json();

          if (data.transcript) {
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              role: 'user',
              content: data.transcript,
              timestamp: new Date().toISOString(),
            }]);
          }
          if (data.response) {
            setMessages(prev => [...prev, {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: data.response,
              timestamp: new Date().toISOString(),
              model: data.model_used,
              hasAudio: !!data.audio,
            }]);
            if (mode === 'presentation') {
              if (data.audio) {
                playAudio(data.audio);
                iframeRef.current?.contentWindow?.postMessage(
                  { type: 'speak-audio', audio: data.audio }, '*'
                );
                setSessionCost(prev => prev + 0.015);
              } else if (data.response) {
                iframeRef.current?.contentWindow?.postMessage(
                  { type: 'speak-text', text: data.response }, '*'
                );
              }
            }
          }
        } catch (err) {
          console.error('Voice processing failed:', err);
        } finally {
          setIsLoading(false);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);

      // Auto-stop after 30 seconds
      setTimeout(() => {
        if (recorder.state === 'recording') {
          recorder.stop();
          setIsRecording(false);
        }
      }, 30000);
    } catch (err) {
      console.error('Microphone access denied:', err);
    }
  }, [isRecording, mode, playAudio]);

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Top bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 16px', borderBottom: '1px solid var(--border)',
        background: 'var(--panel)',
        minHeight: 48,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Sparkles size={16} color="#b8960c" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#1a1a1a' }}>MAX — Empire AI</span>
        </div>
        <ModeToggle mode={mode} onChange={handleModeChange} />
      </div>

      {/* Main content — stack vertically on mobile via CSS */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Avatar panel (presentation mode only) */}
        <AvatarPanel mode={mode} isSpeaking={isSpeaking} isThinking={isLoading} iframeRef={iframeRef} />

        {/* Chat panel */}
        <div style={{
          flex: 1,
          display: 'flex', flexDirection: 'column',
          background: 'var(--chat-bg)',
          position: 'relative',
        }}>
          {/* Messages */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
            {messages.length === 0 && (
              <div style={{
                textAlign: 'center', padding: '60px 20px',
                color: '#999', fontSize: 13,
              }}>
                <Sparkles size={32} color="#b8960c" style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                <div style={{ fontWeight: 600, color: '#666', marginBottom: 4 }}>
                  {mode === 'presentation' ? 'Presentation Mode' : mode === 'compact' ? 'Compact Mode' : 'Text Mode'}
                </div>
                <div>Ask MAX anything. {mode === 'presentation' ? 'Voice + avatar active.' : 'Text responses only.'}</div>
                <div style={{ marginTop: 8, fontSize: 10, color: '#bbb' }}>Ctrl+Shift+P to cycle modes</div>
              </div>
            )}

            {messages.map(msg => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 12,
                }}
              >
                <div style={{
                  maxWidth: '80%',
                  padding: '10px 14px',
                  borderRadius: 12,
                  fontSize: 13,
                  lineHeight: 1.5,
                  background: msg.role === 'user' ? '#fdf8eb' : '#f5f3ef',
                  border: msg.role === 'user' ? '1px solid #f0e6c0' : '1px solid #e5e2dc',
                  color: '#1a1a1a',
                }}>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    marginTop: 4, fontSize: 9, color: '#999',
                  }}>
                    {msg.desk && msg.desk !== 'general' && (
                      <span style={{
                        background: '#f0e6c0', color: '#96750a',
                        padding: '1px 6px', borderRadius: 4, fontWeight: 600,
                      }}>
                        {msg.desk}
                      </span>
                    )}
                    {msg.model && (
                      <span>{msg.model}</span>
                    )}
                    {msg.hasAudio && <span>with voice</span>}
                    <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '10px 14px', color: '#999', fontSize: 13,
              }}>
                <div style={{ display: 'flex', gap: 4 }}>
                  {[0, 1, 2].map(i => (
                    <div key={i} style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: '#b8960c',
                      animation: `dot-bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                    }} />
                  ))}
                </div>
                MAX is thinking...
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Input bar */}
          <div style={{
            padding: '10px 16px',
            borderTop: '1px solid var(--border)',
            background: 'var(--panel)',
          }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <div style={{ position: 'relative', flexShrink: 0 }}>
                <button
                  onClick={toggleRecording}
                  style={{
                    width: 44, height: 44, borderRadius: 10,
                    border: isRecording ? '2px solid #E24B4A' : '1px solid #e5e2dc',
                    background: isRecording ? '#E24B4A' : '#fff',
                    cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: isRecording ? '#fff' : '#999',
                    transition: 'all 0.15s ease',
                    animation: isRecording ? 'mic-pulse 1.5s ease-in-out infinite' : 'none',
                  }}
                  title={isRecording ? 'Stop recording' : 'Start voice input'}
                >
                  {isRecording ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
                {isRecording && (
                  <span style={{
                    position: 'absolute', top: -20, left: '50%', transform: 'translateX(-50%)',
                    fontSize: 10, color: '#E24B4A', fontWeight: 600, whiteSpace: 'nowrap',
                  }}>
                    Listening...
                  </span>
                )}
              </div>

              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
                placeholder="Type or ask MAX..."
                style={{
                  flex: 1, height: 44,
                  border: '1px solid #e5e2dc',
                  borderRadius: 10,
                  padding: '0 14px',
                  fontSize: 13,
                  background: '#fff',
                  outline: 'none',
                  color: '#1a1a1a',
                }}
              />

              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isLoading}
                style={{
                  width: 44, height: 44, borderRadius: 10,
                  border: 'none',
                  background: input.trim() ? '#b8960c' : '#e5e2dc',
                  cursor: input.trim() ? 'pointer' : 'default',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff',
                  transition: 'all 0.15s ease',
                  flexShrink: 0,
                }}
                title="Send message"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '4px 16px',
        borderTop: '1px solid var(--border)',
        background: 'var(--panel)',
        fontSize: 10, color: '#999',
        minHeight: 28,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {connected ? <Wifi size={10} color="#22c55e" /> : <WifiOff size={10} color="#ef4444" />}
            {connected ? 'Connected' : 'Disconnected'}
          </span>
          <span>18 desks</span>
          <span>Grok TTS Rex</span>
          <span>Quality engine active</span>
        </div>
        <span style={{ fontWeight: 600, color: sessionCost > 0 ? '#b8960c' : '#999' }}>
          ${sessionCost.toFixed(3)} session
        </span>
      </div>

      {/* Compact mode: floating mini avatar */}
      {mode === 'compact' && (
        <MiniAvatar
          onClick={() => handleModeChange('presentation')}
          isSpeaking={isSpeaking}
          isThinking={isLoading}
        />
      )}

      <style>{`
        @keyframes dot-bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-8px); opacity: 1; }
        }
        @keyframes speak-bar {
          0%, 100% { height: 4px; }
          50% { height: 20px; }
        }
        @keyframes mic-pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(226, 75, 74, 0.4); }
          50% { box-shadow: 0 0 0 8px rgba(226, 75, 74, 0); }
        }
      `}</style>
    </div>
  );
}
