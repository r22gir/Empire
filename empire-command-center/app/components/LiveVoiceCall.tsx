'use client';
/**
 * MAX Live Voice — tap-to-talk live call with Max over xAI Grok realtime.
 * (2026-09-29, Phase B)
 *
 * Browser <-> our backend WebSocket (/api/v1/avatar/live). The xAI key never
 * reaches the browser. Mic audio: AudioWorklet -> 24 kHz PCM16 binary frames.
 * Max's audio: 24 kHz PCM16 binary frames scheduled on the same AudioContext,
 * flushed immediately on {"type":"interrupt"} (barge-in).
 *
 * Mobile Safari/Chrome: the AudioContext is created and resumed inside the tap
 * handler (user gesture) and getUserMedia needs https (studio.empirebox.store)
 * or localhost.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { API } from '../lib/api';
import { useAssistantName } from '../lib/assistant';

const FAMILY_EDITION = ['amp', 'maxine'].includes((process.env.NEXT_PUBLIC_EMPIRE_EDITION || '').trim().toLowerCase());
const LIVE_STATUS_ES: Record<string, string> = {
  'Connecting…': 'Conectando…',
  'Live — just talk': 'En vivo — habla con normalidad',
  'Listening…': 'Escuchando…',
  'Thinking…': 'Pensando…',
};

type CallState = 'idle' | 'connecting' | 'live' | 'ending' | 'error';
type Line = { id: string; role: 'user' | 'assistant' | 'system'; text: string; final: boolean };

const SAMPLE_RATE = 24000;
// While Max is talking, only forward mic chunks louder than this RMS (the
// rest is sent as silence) so speaker echo cannot barge in on Max himself.
const BARGE_IN_RMS = 0.045;

function liveUrl(): string {
  const base = API.replace(/\/$/, '');
  if (base.startsWith('https://')) return base.replace(/^https:/, 'wss:') + '/avatar/live';
  if (base.startsWith('http://')) return base.replace(/^http:/, 'ws:') + '/avatar/live';
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}${base}/avatar/live`;
}

function fmt(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

export function useLiveVoice() {
  const [state, setState] = useState<CallState>('idle');
  const [lines, setLines] = useState<Line[]>([]);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [cap, setCap] = useState<number>(600);
  const [status, setStatus] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [speaking, setSpeaking] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const nodeRef = useRef<AudioNode | null>(null);
  const sourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const playHeadRef = useRef<number>(0);
  const endAtRef = useRef<number>(0);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stateRef = useRef<CallState>('idle');

  const setCallState = (s: CallState) => { stateRef.current = s; setState(s); };

  const upsertLine = useCallback((key: string, role: Line['role'], text: string, final: boolean, append: boolean) => {
    setLines(prev => {
      const idx = prev.findIndex(l => l.id === key);
      if (idx === -1) return [...prev, { id: key, role, text, final }].slice(-60);
      const next = prev.slice();
      next[idx] = { ...next[idx], text: append ? next[idx].text + text : (text || next[idx].text), final };
      return next;
    });
  }, []);

  const isPlaying = () => {
    const ctx = ctxRef.current;
    return !!ctx && playHeadRef.current > ctx.currentTime + 0.02;
  };

  const flushPlayback = useCallback(() => {
    for (const s of sourcesRef.current) { try { s.stop(); } catch { /* already stopped */ } }
    sourcesRef.current = [];
    const ctx = ctxRef.current;
    playHeadRef.current = ctx ? ctx.currentTime : 0;
    setSpeaking(false);
  }, []);

  const playPcm = useCallback((buf: ArrayBuffer) => {
    const ctx = ctxRef.current;
    if (!ctx || buf.byteLength < 2) return;
    const pcm = new Int16Array(buf, 0, Math.floor(buf.byteLength / 2));
    const audio = ctx.createBuffer(1, pcm.length, SAMPLE_RATE);
    const ch = audio.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 32768;
    const src = ctx.createBufferSource();
    src.buffer = audio;
    src.connect(ctx.destination);
    const startAt = Math.max(ctx.currentTime + 0.03, playHeadRef.current);
    src.start(startAt);
    playHeadRef.current = startAt + audio.duration;
    sourcesRef.current.push(src);
    setSpeaking(true);
    src.onended = () => {
      sourcesRef.current = sourcesRef.current.filter(s => s !== src);
      if (sourcesRef.current.length === 0) setSpeaking(false);
    };
  }, []);

  const cleanup = useCallback((finalState: CallState = 'idle') => {
    if (tickRef.current) { clearInterval(tickRef.current); tickRef.current = null; }
    try { wsRef.current?.close(); } catch { /* ignore */ }
    wsRef.current = null;
    flushPlayback();
    try { nodeRef.current?.disconnect(); } catch { /* ignore */ }
    nodeRef.current = null;
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    const ctx = ctxRef.current;
    ctxRef.current = null;
    if (ctx) ctx.close().catch(() => undefined);
    setRemaining(null);
    setCallState(finalState);
  }, [flushPlayback]);

  const stop = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      setCallState('ending');
      try { ws.send(JSON.stringify({ type: 'hangup' })); } catch { /* ignore */ }
      setTimeout(() => cleanup('idle'), 400);
    } else {
      cleanup('idle');
    }
  }, [cleanup]);

  const start = useCallback(async () => {
    if (stateRef.current === 'connecting' || stateRef.current === 'live') return;
    setError('');
    setLines([]);
    setStatus('Connecting…');
    setCallState('connecting');
    // 1) AudioContext inside the user gesture (iOS Safari requirement).
    const AC: typeof AudioContext = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!AC || !navigator.mediaDevices?.getUserMedia) {
      setError('This browser cannot do live audio (needs https + a modern browser).');
      setCallState('error');
      return;
    }
    const ctx = new AC();
    ctxRef.current = ctx;
    try { await ctx.resume(); } catch { /* resumed later */ }
    // Unlock output on iOS with a 1-sample silent buffer (still in gesture).
    try { const b = ctx.createBuffer(1, 1, 22050); const s = ctx.createBufferSource(); s.buffer = b; s.connect(ctx.destination); s.start(0); } catch { /* ignore */ }
    playHeadRef.current = ctx.currentTime;

    // 2) Mic + WebSocket in parallel.
    let stream: MediaStream;
    const ws = new WebSocket(liveUrl());
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;
    // Attach handlers immediately: the server can answer (ready / error) before
    // the mic permission prompt and AudioWorklet load finish.
    ws.onmessage = (ev: MessageEvent) => {
      if (ev.data instanceof ArrayBuffer) {
        const copy = ev.data.slice(0);
        playPcm(ev.data);
        window.dispatchEvent(new CustomEvent('max-live-pcm', {
          detail: { pcm: copy, sampleRate: SAMPLE_RATE },
        }));
        return;
      }
      let msg: any;
      try { msg = JSON.parse(ev.data); } catch { return; }
      switch (msg.type) {
        case 'ready':
          setCap(msg.cap_seconds || 600);
          endAtRef.current = Date.now() + (msg.cap_seconds || 600) * 1000;
          setRemaining(msg.cap_seconds || 600);
          if (tickRef.current) clearInterval(tickRef.current);
          tickRef.current = setInterval(() => setRemaining(Math.max(0, Math.round((endAtRef.current - Date.now()) / 1000))), 500);
          setCallState('live');
          setStatus('Live — just talk');
          break;
        case 'session_ready':
          setStatus('Live — just talk');
          break;
        case 'interrupt':
          flushPlayback();
          break;
        case 'speech_started':
          setStatus('Listening…');
          break;
        case 'speech_stopped':
          setStatus('Thinking…');
          break;
        case 'transcript': {
          if (msg.role === 'user') {
            upsertLine(`u-${msg.item_id || 'cur'}`, 'user', msg.text || '', !!msg.final, false);
          } else if (msg.role === 'assistant') {
            const key = `a-${msg.response_id || 'cur'}`;
            if (msg.final) upsertLine(key, 'assistant', msg.text || '', true, false);
            else upsertLine(key, 'assistant', msg.delta || '', false, true);
          }
          break;
        }
        case 'tool':
          setStatus(msg.status === 'running' ? `Looking up (${String(msg.name).replace(/_/g, ' ')})…` : 'Live — just talk');
          break;
        case 'response_done':
          setStatus('Live — just talk');
          break;
        case 'ping':
          if (typeof msg.remaining === 'number') endAtRef.current = Date.now() + msg.remaining * 1000;
          try { ws.send(JSON.stringify({ type: 'ping' })); } catch { /* ignore */ }
          break;
        case 'warning':
          upsertLine(`w-${Date.now()}`, 'system', `Call ends in ${msg.remaining}s (10-minute cap).`, true, false);
          break;
        case 'error':
          setError(msg.message || 'Voice error');
          break;
        case 'ended':
          upsertLine(`e-${Date.now()}`, 'system', msg.reason === 'cap_reached' ? 'Call ended — 10-minute cap reached.' : 'Call ended.', true, false);
          cleanup(msg.reason === 'unavailable' || msg.reason === 'upstream_connect_failed' ? 'error' : 'idle');
          break;
      }
    };
    ws.onerror = () => { setError('Connection error (are you signed in to studio.empirebox.store?)'); };
    ws.onclose = () => { if (stateRef.current !== 'idle' && stateRef.current !== 'error') cleanup('idle'); };
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
    } catch (e: any) {
      setError(e?.name === 'NotAllowedError' ? 'Microphone permission was denied.' : `Microphone unavailable: ${e?.message || e}`);
      cleanup('error');
      return;
    }
    if (wsRef.current !== ws || ctxRef.current !== ctx) {
      // Call ended (error/hangup) while the mic prompt was open.
      stream.getTracks().forEach(t => t.stop());
      return;
    }
    streamRef.current = stream;
    const source = ctx.createMediaStreamSource(stream);

    const sendChunk = (pcm: ArrayBuffer, rms: number) => {
      const sock = wsRef.current;
      if (!sock || sock.readyState !== WebSocket.OPEN) return;
      if (isPlaying() && rms < BARGE_IN_RMS) {
        sock.send(new ArrayBuffer(pcm.byteLength)); // silence keeps VAD timing steady
      } else {
        sock.send(pcm);
      }
    };

    try {
      if (ctx.audioWorklet) {
        await ctx.audioWorklet.addModule('/max-mic-worklet.js');
        if (ctxRef.current !== ctx) return; // call ended while loading
        const node = new AudioWorkletNode(ctx, 'max-mic-processor', { processorOptions: { targetRate: SAMPLE_RATE } });
        node.port.onmessage = (ev: MessageEvent) => sendChunk(ev.data.pcm, ev.data.rms);
        source.connect(node);
        // Keep the graph pulling without making the mic audible.
        const mute = ctx.createGain(); mute.gain.value = 0;
        node.connect(mute); mute.connect(ctx.destination);
        nodeRef.current = node;
      } else {
        // Fallback for old engines: ScriptProcessor + naive resample.
        const proc = ctx.createScriptProcessor(4096, 1, 1);
        const ratio = ctx.sampleRate / SAMPLE_RATE;
        proc.onaudioprocess = (e: AudioProcessingEvent) => {
          const inp = e.inputBuffer.getChannelData(0);
          const n = Math.floor(inp.length / ratio);
          const out = new Int16Array(n);
          let sum = 0;
          for (let i = 0; i < n; i++) {
            const s = Math.max(-1, Math.min(1, inp[Math.floor(i * ratio)]));
            sum += s * s;
            out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }
          sendChunk(out.buffer, Math.sqrt(sum / Math.max(1, n)));
        };
        source.connect(proc);
        const mute = ctx.createGain(); mute.gain.value = 0;
        proc.connect(mute); mute.connect(ctx.destination);
        nodeRef.current = proc;
      }
    } catch (e: any) {
      setError(`Audio setup failed: ${e?.message || e}`);
      cleanup('error');
      return;
    }

  }, [cleanup, flushPlayback, playPcm, upsertLine]);

  useEffect(() => () => cleanup('idle'), [cleanup]);

  return { state, lines, remaining, cap, status, error, speaking, start, stop };
}

export default function LiveVoiceCall({ variant = 'floating' }: { variant?: 'floating' | 'inline' }) {
  const v = useLiveVoice();
  const active = v.state === 'connecting' || v.state === 'live' || v.state === 'ending';
  const assistant = useAssistantName();
  const who = FAMILY_EDITION ? assistant : 'Max';
  const statusText = FAMILY_EDITION
    ? (LIVE_STATUS_ES[v.status] || (v.status.startsWith('Looking up') ? 'Buscando…' : v.status))
    : v.status;
  const [open, setOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => { if (active) setOpen(true); }, [active]);
  useEffect(() => { scrollRef.current?.scrollTo({ top: 1e9 }); }, [v.lines]);

  const onTap = () => { if (active) v.stop(); else { setOpen(true); v.start(); } };

  const btnStyle: React.CSSProperties = {
    width: 58, height: 58, borderRadius: '50%', border: 'none', cursor: 'pointer',
    background: active ? '#dc2626' : 'linear-gradient(135deg,#b8860b,#d4af37)',
    color: '#fff', boxShadow: active ? '0 0 0 6px rgba(220,38,38,0.25)' : '0 4px 14px rgba(0,0,0,0.35)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26,
    touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent',
  };
  const wrap: React.CSSProperties = variant === 'floating'
    ? { position: 'fixed', right: 16, bottom: 'calc(112px + env(safe-area-inset-bottom))', zIndex: 9990, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }
    : { display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10, position: 'relative' };

  return (
    <div style={wrap} data-testid="max-live-voice">
      {open && (
        <div style={{
          width: 'min(92vw, 360px)', maxHeight: '55vh', background: 'rgba(17,17,20,0.96)', color: '#eee',
          border: '1px solid rgba(212,175,55,0.45)', borderRadius: 14, padding: 12, display: 'flex', flexDirection: 'column', gap: 8,
          boxShadow: '0 10px 30px rgba(0,0,0,0.5)', fontSize: 14,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <strong style={{ color: '#d4af37' }}>{FAMILY_EDITION ? `${who} · Voz en vivo` : 'Max · Live voice'}</strong>
            <span style={{ fontVariantNumeric: 'tabular-nums', color: (v.remaining ?? 999) <= 30 ? '#f87171' : '#aaa' }}>
              {v.remaining !== null ? (FAMILY_EDITION ? `quedan ${fmt(v.remaining)}` : `${fmt(v.remaining)} left`) : (FAMILY_EDITION ? `máx. ${fmt(v.cap)}` : `cap ${fmt(v.cap)}`)}
            </span>
            {!active && <button onClick={() => setOpen(false)} aria-label={FAMILY_EDITION ? 'Cerrar' : 'Close'} style={{ background: 'none', border: 'none', color: '#aaa', fontSize: 18, cursor: 'pointer' }}>×</button>}
          </div>
          <div style={{ fontSize: 12, color: v.error ? '#f87171' : '#9ca3af' }}>
            {v.error || (active
              ? `${statusText}${v.speaking ? (FAMILY_EDITION ? ` · ${who} está hablando` : ' · Max speaking') : ''}`
              : (FAMILY_EDITION ? 'Toca el micrófono para empezar una llamada en vivo (máximo 10 minutos).' : 'Tap the mic to start a live call (10-min cap).'))}
          </div>
          <div ref={scrollRef} style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6, minHeight: 60 }}>
            {v.lines.length === 0 && <div style={{ color: '#6b7280', fontSize: 12 }}>{FAMILY_EDITION ? 'Aquí aparece la transcripción.' : 'Transcript appears here.'}</div>}
            {v.lines.map(l => (
              <div key={l.id} style={{
                alignSelf: l.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '88%',
                background: l.role === 'user' ? '#1f2937' : l.role === 'assistant' ? 'rgba(212,175,55,0.12)' : 'transparent',
                color: l.role === 'system' ? '#9ca3af' : '#eee', borderRadius: 10, padding: l.role === 'system' ? 0 : '6px 9px',
                fontStyle: l.role === 'system' ? 'italic' : 'normal', opacity: l.final ? 1 : 0.8, fontSize: l.role === 'system' ? 12 : 14,
              }}>{l.text || '…'}</div>
            ))}
          </div>
        </div>
      )}
      <button onClick={onTap} style={btnStyle} aria-label={FAMILY_EDITION ? (active ? `Terminar la llamada con ${who}` : `Empezar llamada en vivo con ${who}`) : (active ? 'End live call with Max' : 'Start live call with Max')}
        title={FAMILY_EDITION ? (active ? 'Terminar llamada' : `Hablar con ${who} (en vivo)`) : (active ? 'End call' : 'Talk to Max (live)')}>
        {active ? '■' : '🎙️'}
      </button>
    </div>
  );
}
