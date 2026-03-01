'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { Mic, MicOff, Phone, PhoneOff, X, Volume2, Minimize2, Maximize2, GripHorizontal } from 'lucide-react';

interface TranscriptEntry {
  role: 'user' | 'assistant';
  text: string;
}

const SYSTEM_PROMPT =
  'You are MAX, the AI Director for the entire Empire ecosystem. ' +
  'Bilingual English/Spanish. Keep voice responses concise. ' +
  'You oversee ALL businesses: WorkroomForge (DC window treatments), LuxeForge (designer portal), ' +
  'AMP (Cali Colombia, 9 services), SocialForge (in dev), CRM Personal, Empire Box. ' +
  'Help the founder with anything across every business.';

export default function VoiceAgent({ onClose }: { onClose: () => void }) {
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'error'>('idle');
  const [isTalking, setIsTalking] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [currentAssistantText, setCurrentAssistantText] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [minimized, setMinimized] = useState(false);

  // Dragging state
  const [position, setPosition] = useState({ x: window.innerWidth - 500, y: window.innerHeight - 480 });
  const [size, setSize] = useState({ w: 460, h: 420 });
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const micCaptureCtxRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const playbackQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const currentTranscriptRef = useRef('');

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, currentAssistantText]);

  /* ── Drag handling ─────────────────────────────────── */
  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { startX: e.clientX, startY: e.clientY, origX: position.x, origY: position.y };

    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = ev.clientX - dragRef.current.startX;
      const dy = ev.clientY - dragRef.current.startY;
      setPosition({
        x: Math.max(0, Math.min(window.innerWidth - size.w, dragRef.current.origX + dx)),
        y: Math.max(0, Math.min(window.innerHeight - size.h, dragRef.current.origY + dy)),
      });
    };
    const onUp = () => {
      dragRef.current = null;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [position, size]);

  /* ── Connect ─────────────────────────────────────────── */
  const connect = useCallback(async () => {
    setStatus('connecting');
    setErrorMsg('');
    try {
      const tokenRes = await fetch('/api/voice-token', { method: 'POST' });
      const tokenData = await tokenRes.json();
      if (!tokenRes.ok) throw new Error(tokenData.error || 'Failed to get token');

      const secret = tokenData.client_secret?.value || tokenData.token || tokenData.secret;
      if (!secret) throw new Error('No ephemeral token in response');

      const ws = new WebSocket(
        'wss://api.x.ai/v1/realtime',
        [`xai-client-secret.${secret}`],
      );
      wsRef.current = ws;

      ws.onopen = async () => {
        setStatus('connected');
        if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
          audioCtxRef.current = new AudioContext({ sampleRate: 24000 });
        }
        if (audioCtxRef.current.state === 'suspended') {
          await audioCtxRef.current.resume();
        }
        ws.send(JSON.stringify({
          type: 'session.update',
          session: {
            instructions: SYSTEM_PROMPT,
            voice: 'Rex',
            turn_detection: { type: 'server_vad', threshold: 0.3, silence_duration_ms: 800 },
            input_audio_transcription: { model: 'grok-2-latest' },
            audio: {
              input: { format: { type: 'audio/pcm', rate: 24000 } },
              output: { format: { type: 'audio/pcm', rate: 24000 } },
            },
          },
        }));
      };

      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        handleServerEvent(msg);
      };

      ws.onerror = () => {
        setErrorMsg('WebSocket connection error');
        setStatus('error');
      };

      ws.onclose = () => {
        if (status !== 'error') setStatus('idle');
      };
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Connection failed');
      setStatus('error');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Server events ───────────────────────────────────── */
  const handleServerEvent = useCallback((msg: { type: string; delta?: string; transcript?: string; [key: string]: unknown }) => {
    switch (msg.type) {
      case 'response.output_audio.delta':
        if (msg.delta) queueAudioChunk(msg.delta);
        break;

      case 'response.output_audio_transcript.delta':
        if (msg.delta) {
          currentTranscriptRef.current += msg.delta;
          setCurrentAssistantText(currentTranscriptRef.current);
        }
        break;

      case 'response.output_audio_transcript.done':
      case 'response.done':
        if (currentTranscriptRef.current) {
          const text = currentTranscriptRef.current;
          setTranscript(prev => [...prev, { role: 'assistant', text }]);
          currentTranscriptRef.current = '';
          setCurrentAssistantText('');
        }
        break;

      case 'conversation.item.input_audio_transcription.completed':
        if (msg.transcript) {
          setTranscript(prev => [...prev, { role: 'user', text: msg.transcript as string }]);
        }
        break;

      case 'error':
        setErrorMsg(JSON.stringify((msg as Record<string, unknown>).error || 'Server error'));
        break;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Audio playback ──────────────────────────────────── */
  const queueAudioChunk = useCallback((base64: string) => {
    const bytes = atob(base64);
    const buf = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) buf[i] = bytes.charCodeAt(i);
    const pcm16 = new Int16Array(buf.buffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) float32[i] = pcm16[i] / 32768.0;
    playbackQueueRef.current.push(float32);
    if (!isPlayingRef.current) drainPlaybackQueue();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const drainPlaybackQueue = useCallback(async () => {
    const ctx = audioCtxRef.current;
    if (!ctx || isPlayingRef.current) return;
    isPlayingRef.current = true;

    while (playbackQueueRef.current.length > 0) {
      const chunk = playbackQueueRef.current.shift()!;
      const audioBuf = ctx.createBuffer(1, chunk.length, 24000);
      audioBuf.getChannelData(0).set(chunk);
      const src = ctx.createBufferSource();
      src.buffer = audioBuf;
      src.connect(ctx.destination);
      src.start();
      await new Promise<void>(r => { src.onended = () => r(); });
    }
    isPlayingRef.current = false;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Mic capture ─────────────────────────────────────── */
  const micWorkletReadyRef = useRef(false);
  const micSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

  const startMic = useCallback(async () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      micStreamRef.current = stream;

      let micCtx = micCaptureCtxRef.current;
      if (!micCtx || micCtx.state === 'closed') {
        // Use device native sample rate — the worklet resamples to 24kHz
        micCtx = new AudioContext();
        micCaptureCtxRef.current = micCtx;
        micWorkletReadyRef.current = false;
      }

      if (micCtx.state === 'suspended') {
        await micCtx.resume();
      }

      const nativeRate = micCtx.sampleRate;
      const TARGET_RATE = 24000;

      if (!micWorkletReadyRef.current) {
        const workletCode = `
          class PCMProcessor extends AudioWorkletProcessor {
            constructor() {
              super();
              this._nativeRate = ${nativeRate};
              this._targetRate = ${TARGET_RATE};
              this._ratio = this._nativeRate / this._targetRate;
            }
            process(inputs) {
              const input = inputs[0][0];
              if (!input) return true;
              if (this._nativeRate === this._targetRate) {
                this.port.postMessage(input);
              } else {
                const outLen = Math.floor(input.length / this._ratio);
                const out = new Float32Array(outLen);
                for (let i = 0; i < outLen; i++) {
                  out[i] = input[Math.floor(i * this._ratio)];
                }
                this.port.postMessage(out);
              }
              return true;
            }
          }
          registerProcessor('pcm-capture', PCMProcessor);
        `;
        const blob = new Blob([workletCode], { type: 'application/javascript' });
        const url = URL.createObjectURL(blob);
        await micCtx.audioWorklet.addModule(url);
        URL.revokeObjectURL(url);
        micWorkletReadyRef.current = true;
      }

      const source = micCtx.createMediaStreamSource(stream);
      micSourceRef.current = source;
      const worklet = new AudioWorkletNode(micCtx, 'pcm-capture');
      workletNodeRef.current = worklet;

      worklet.port.onmessage = (e: MessageEvent<Float32Array>) => {
        if (ws.readyState !== WebSocket.OPEN) return;
        const float32 = e.data;
        const pcm16 = new Int16Array(float32.length);
        for (let i = 0; i < float32.length; i++) {
          const s = Math.max(-1, Math.min(1, float32[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        const bytes = new Uint8Array(pcm16.buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
        const base64 = btoa(binary);
        ws.send(JSON.stringify({ type: 'input_audio_buffer.append', audio: base64 }));
      };

      source.connect(worklet);
      worklet.connect(micCtx.destination);
      setIsTalking(true);
    } catch (err: unknown) {
      console.error('Mic start failed:', err);
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes('NotAllowed') || msg.includes('Permission')) {
        setErrorMsg('Microphone access denied — allow mic in browser settings, then retry');
      } else if (msg.includes('NotFound') || msg.includes('DevicesNotFound')) {
        setErrorMsg('No microphone found — check your audio devices');
      } else {
        setErrorMsg(`Microphone error: ${msg}`);
      }
    }
  }, []);

  const stopMic = useCallback(() => {
    const ws = wsRef.current;

    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;
    micSourceRef.current?.disconnect();
    micSourceRef.current = null;

    micStreamRef.current?.getTracks().forEach(t => t.stop());
    micStreamRef.current = null;

    setIsTalking(false);

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'input_audio_buffer.commit' }));
      ws.send(JSON.stringify({
        type: 'response.create',
        response: { modalities: ['text', 'audio'] },
      }));
    }
  }, []);

  /* ── Disconnect ──────────────────────────────────────── */
  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    micStreamRef.current?.getTracks().forEach(t => t.stop());
    micStreamRef.current = null;
    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;
    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    micCaptureCtxRef.current?.close();
    micCaptureCtxRef.current = null;
    playbackQueueRef.current = [];
    isPlayingRef.current = false;
    setIsTalking(false);
    setStatus('idle');
  }, []);

  /* ── Cleanup on unmount ──────────────────────────────── */
  useEffect(() => {
    return () => {
      wsRef.current?.close();
      micStreamRef.current?.getTracks().forEach(t => t.stop());
      workletNodeRef.current?.disconnect();
      audioCtxRef.current?.close();
      micCaptureCtxRef.current?.close();
    };
  }, []);

  const isConnected = status === 'connected';

  // Minimized: compact floating pill
  if (minimized) {
    return (
      <div
        style={{
          position: 'fixed',
          right: 16,
          bottom: 16,
          zIndex: 55,
          background: 'var(--surface)',
          border: '1px solid var(--gold-border)',
          borderRadius: '16px',
          padding: '8px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          cursor: 'pointer',
        }}
        onClick={() => setMinimized(false)}
      >
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #D4AF37, #8B5CF6)' }}
        >
          <Volume2 className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="text-xs font-semibold text-gold-shimmer">MAX Voice</span>
        <span className="text-[10px]" style={{ color: isConnected ? '#22c55e' : 'var(--text-muted)' }}>
          {isConnected ? '● Live' : '○ Off'}
        </span>
        <Maximize2 className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        width: size.w,
        height: size.h,
        zIndex: 55,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: '16px',
        overflow: 'hidden',
        boxShadow: '0 12px 48px rgba(0,0,0,0.6), 0 0 0 1px var(--gold-border)',
        background: 'var(--surface)',
        resize: 'both',
        minWidth: 320,
        minHeight: 280,
      }}
    >
      {/* ── Header / Drag handle ────────────────────────── */}
      <div
        className="px-4 py-3 flex items-center justify-between shrink-0"
        style={{
          borderBottom: '1px solid var(--border)',
          background: 'var(--raised)',
          cursor: 'grab',
        }}
        onMouseDown={onDragStart}
      >
        <div className="flex items-center gap-2">
          <GripHorizontal className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #D4AF37, #8B5CF6)' }}
          >
            <Volume2 className="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <span className="font-bold text-xs text-gold-shimmer tracking-wide">MAX Voice</span>
            <span className="text-[10px] ml-2" style={{ color: 'var(--text-muted)' }}>
              {status === 'idle' ? 'Disconnected' :
               status === 'connecting' ? 'Connecting…' :
               status === 'error' ? 'Error' : 'Live · Rex'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => { e.stopPropagation(); setMinimized(true); }}
            className="w-6 h-6 rounded flex items-center justify-center transition"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--hover)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            <Minimize2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); disconnect(); onClose(); }}
            className="w-6 h-6 rounded flex items-center justify-center transition"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--hover)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ── Transcript ────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5">
        {transcript.length === 0 && !currentAssistantText && (
          <p className="text-center text-xs py-6" style={{ color: 'var(--text-muted)' }}>
            {isConnected
              ? 'Hold the mic button and speak to MAX'
              : 'Press Connect to start a voice conversation'}
          </p>
        )}
        {transcript.map((entry, i) => (
          <div
            key={i}
            className="rounded-lg px-3 py-2 text-xs"
            style={
              entry.role === 'user'
                ? {
                    background: 'var(--gold-pale)',
                    border: '1px solid var(--gold-border)',
                    color: 'var(--text-primary)',
                    marginLeft: '1.5rem',
                  }
                : {
                    background: 'var(--raised)',
                    border: '1px solid var(--border)',
                    color: 'var(--text-primary)',
                    marginRight: '1.5rem',
                  }
            }
          >
            <span className="text-[10px] font-semibold block mb-0.5" style={{ color: entry.role === 'user' ? 'var(--gold)' : 'var(--purple)' }}>
              {entry.role === 'user' ? 'You' : 'MAX'}
            </span>
            {entry.text}
          </div>
        ))}
        {currentAssistantText && (
          <div
            className="rounded-lg px-3 py-2 text-xs"
            style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)', marginRight: '1.5rem' }}
          >
            <span className="text-[10px] font-semibold block mb-0.5" style={{ color: 'var(--purple)' }}>MAX</span>
            {currentAssistantText}
            <span className="streaming-cursor" />
          </div>
        )}
        <div ref={transcriptEndRef} />
      </div>

      {/* ── Error ─────────────────────────────────────── */}
      {errorMsg && (
        <div
          className="mx-3 mb-2 px-3 py-1.5 rounded-lg text-[10px]"
          style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}
        >
          {errorMsg}
        </div>
      )}

      {/* ── Controls ──────────────────────────────────── */}
      <div
        className="px-4 py-3 flex items-center justify-center gap-3 shrink-0"
        style={{ borderTop: '1px solid var(--border)', background: 'var(--raised)' }}
      >
        {!isConnected ? (
          <button
            onClick={connect}
            disabled={status === 'connecting'}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold transition"
            style={{
              background: status === 'connecting' ? 'var(--elevated)' : 'var(--gold)',
              color: status === 'connecting' ? 'var(--text-muted)' : '#0a0a0a',
              border: '1px solid var(--gold-border)',
            }}
          >
            <Phone className="w-3.5 h-3.5" />
            {status === 'connecting' ? 'Connecting…' : 'Connect'}
          </button>
        ) : (
          <>
            {/* Push-to-talk button */}
            <button
              onMouseDown={startMic}
              onMouseUp={stopMic}
              onMouseLeave={() => { if (isTalking) stopMic(); }}
              onTouchStart={startMic}
              onTouchEnd={stopMic}
              className="w-14 h-14 rounded-full flex items-center justify-center transition-all"
              style={{
                background: isTalking
                  ? 'linear-gradient(135deg, var(--gold-bright), var(--gold))'
                  : 'var(--elevated)',
                border: isTalking ? '2px solid var(--gold)' : '2px solid var(--gold-border)',
                boxShadow: isTalking ? '0 0 24px var(--gold-glow)' : 'none',
                color: isTalking ? '#0a0a0a' : 'var(--gold)',
                transform: isTalking ? 'scale(1.08)' : 'scale(1)',
              }}
            >
              {isTalking ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
            </button>

            {/* Disconnect */}
            <button
              onClick={disconnect}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs transition"
              style={{
                background: 'rgba(239,68,68,0.1)',
                color: '#ef4444',
                border: '1px solid rgba(239,68,68,0.2)',
              }}
            >
              <PhoneOff className="w-3.5 h-3.5" />
              End
            </button>
          </>
        )}
      </div>
    </div>
  );
}
