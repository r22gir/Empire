'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { Mic, MicOff, Phone, PhoneOff, X, Volume2 } from 'lucide-react';

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

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const playbackQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const currentTranscriptRef = useRef('');

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, currentAssistantText]);

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

      ws.onopen = () => {
        setStatus('connected');
        // Initialize AudioContext early so playback works before mic is used
        if (!audioCtxRef.current) {
          audioCtxRef.current = new AudioContext({ sampleRate: 24000 });
        }
        ws.send(JSON.stringify({
          type: 'session.update',
          session: {
            instructions: SYSTEM_PROMPT,
            voice: 'Rex',
            turn_detection: null,
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
  const startMic = useCallback(async () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    if (!audioCtxRef.current) {
      audioCtxRef.current = new AudioContext({ sampleRate: 24000 });
    }
    const ctx = audioCtxRef.current;

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: { ideal: 24000 }, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    micStreamRef.current = stream;

    // Register the PCM capture worklet
    const workletCode = `
      class PCMProcessor extends AudioWorkletProcessor {
        process(inputs) {
          const input = inputs[0][0];
          if (input) this.port.postMessage(input);
          return true;
        }
      }
      registerProcessor('pcm-capture', PCMProcessor);
    `;
    const blob = new Blob([workletCode], { type: 'application/javascript' });
    const url = URL.createObjectURL(blob);
    await ctx.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);

    const source = ctx.createMediaStreamSource(stream);
    const worklet = new AudioWorkletNode(ctx, 'pcm-capture');
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
    worklet.connect(ctx.destination);
    setIsTalking(true);
  }, []);

  const stopMic = useCallback(() => {
    const ws = wsRef.current;

    // Disconnect worklet
    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;

    // Stop mic tracks
    micStreamRef.current?.getTracks().forEach(t => t.stop());
    micStreamRef.current = null;

    setIsTalking(false);

    // Commit and request response
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
    };
  }, []);

  const isConnected = status === 'connected';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(10px)' }}
    >
      <div
        className="w-full max-w-lg rounded-2xl flex flex-col overflow-hidden shadow-2xl"
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--gold-border)',
          maxHeight: '80vh',
        }}
      >
        {/* ── Header ────────────────────────────────────── */}
        <div
          className="px-5 py-4 flex items-center justify-between shrink-0"
          style={{ borderBottom: '1px solid var(--border)', background: 'var(--raised)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #D4AF37, #8B5CF6)' }}
            >
              <Volume2 className="w-4 h-4 text-white" />
            </div>
            <div>
              <span className="font-bold text-sm text-gold-shimmer tracking-wide">MAX Voice</span>
              <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>
                {status === 'idle' ? 'Disconnected' :
                 status === 'connecting' ? 'Connecting…' :
                 status === 'error' ? 'Error' : 'Live · Rex'}
              </span>
            </div>
          </div>
          <button
            onClick={() => { disconnect(); onClose(); }}
            className="w-8 h-8 rounded-lg flex items-center justify-center transition"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--hover)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Transcript ────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3 min-h-[200px]">
          {transcript.length === 0 && !currentAssistantText && (
            <p className="text-center text-sm py-8" style={{ color: 'var(--text-muted)' }}>
              {isConnected
                ? 'Hold the mic button and speak to MAX'
                : 'Press Connect to start a voice conversation'}
            </p>
          )}
          {transcript.map((entry, i) => (
            <div
              key={i}
              className="rounded-xl px-4 py-2.5 text-sm"
              style={
                entry.role === 'user'
                  ? {
                      background: 'var(--gold-pale)',
                      border: '1px solid var(--gold-border)',
                      color: 'var(--text-primary)',
                      marginLeft: '2rem',
                    }
                  : {
                      background: 'var(--raised)',
                      border: '1px solid var(--border)',
                      color: 'var(--text-primary)',
                      marginRight: '2rem',
                    }
              }
            >
              <span className="text-xs font-semibold block mb-1" style={{ color: entry.role === 'user' ? 'var(--gold)' : 'var(--purple)' }}>
                {entry.role === 'user' ? 'You' : 'MAX'}
              </span>
              {entry.text}
            </div>
          ))}
          {currentAssistantText && (
            <div
              className="rounded-xl px-4 py-2.5 text-sm"
              style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)', marginRight: '2rem' }}
            >
              <span className="text-xs font-semibold block mb-1" style={{ color: 'var(--purple)' }}>MAX</span>
              {currentAssistantText}
              <span className="streaming-cursor" />
            </div>
          )}
          <div ref={transcriptEndRef} />
        </div>

        {/* ── Error ─────────────────────────────────────── */}
        {errorMsg && (
          <div
            className="mx-5 mb-3 px-4 py-2 rounded-lg text-xs"
            style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}
          >
            {errorMsg}
          </div>
        )}

        {/* ── Controls ──────────────────────────────────── */}
        <div
          className="px-5 py-4 flex items-center justify-center gap-4 shrink-0"
          style={{ borderTop: '1px solid var(--border)', background: 'var(--raised)' }}
        >
          {!isConnected ? (
            <button
              onClick={connect}
              disabled={status === 'connecting'}
              className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold transition"
              style={{
                background: status === 'connecting' ? 'var(--elevated)' : 'var(--gold)',
                color: status === 'connecting' ? 'var(--text-muted)' : '#0a0a0a',
                border: '1px solid var(--gold-border)',
              }}
            >
              <Phone className="w-4 h-4" />
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
                className="w-16 h-16 rounded-full flex items-center justify-center transition-all"
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
                {isTalking ? <Mic className="w-6 h-6" /> : <MicOff className="w-6 h-6" />}
              </button>

              {/* Disconnect */}
              <button
                onClick={disconnect}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm transition"
                style={{
                  background: 'rgba(239,68,68,0.1)',
                  color: '#ef4444',
                  border: '1px solid rgba(239,68,68,0.2)',
                }}
              >
                <PhoneOff className="w-4 h-4" />
                End
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
