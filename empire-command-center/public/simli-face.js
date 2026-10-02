/**
 * Simli face client. The API key never appears here.
 * Session tokens come from /api/v1/avatar/simli/session.
 * Audio in is PCM16 mono at 16 kHz (Max TTS or xAI live voice).
 */
const SAMPLE_RATE = 16000;

export function apiBase() {
  const host = location.hostname;
  if (host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0') {
    return 'http://localhost:8000/api/v1';
  }
  return `${location.origin}/api/v1`;
}

export async function simliStatus(edition, base) {
  const root = base || apiBase();
  const res = await fetch(`${root}/avatar/simli/status?edition=${encodeURIComponent(edition || 'workroom')}`);
  if (!res.ok) {
    return { enabled: false, renderer: 'talkinghead', reason: 'Simli status unavailable. TalkingHead is the avatar.' };
  }
  return res.json();
}

export async function reportSimliMinutes(edition, seconds, source, base) {
  const root = base || apiBase();
  const body = JSON.stringify({
    edition: edition || 'workroom',
    seconds: Math.max(0, Number(seconds) || 0),
    source: source || 'simli',
  });
  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      if (navigator.sendBeacon(`${root}/avatar/simli/usage`, blob)) return;
    }
  } catch { /* fall through */ }
  await fetch(`${root}/avatar/simli/usage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    keepalive: true,
  });
}

function resampleTo16k(floatSamples, fromRate) {
  if (!floatSamples || !floatSamples.length) return new Int16Array(0);
  const rate = fromRate || SAMPLE_RATE;
  if (rate === SAMPLE_RATE) {
    const pcm = new Int16Array(floatSamples.length);
    for (let i = 0; i < floatSamples.length; i++) {
      const s = Math.max(-1, Math.min(1, floatSamples[i]));
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return pcm;
  }
  const outLen = Math.max(1, Math.round(floatSamples.length * SAMPLE_RATE / rate));
  const pcm = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const src = i * rate / SAMPLE_RATE;
    const i0 = Math.floor(src);
    const i1 = Math.min(i0 + 1, floatSamples.length - 1);
    const frac = src - i0;
    const sample = floatSamples[i0] * (1 - frac) + floatSamples[i1] * frac;
    const clamped = Math.max(-1, Math.min(1, sample));
    pcm[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
  }
  return pcm;
}

export function pcm16FromFloat(floatSamples, fromRate) {
  return resampleTo16k(floatSamples, fromRate);
}

export async function mp3Base64ToPcm16(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const ctx = new AudioContext();
  try {
    const audio = await ctx.decodeAudioData(bytes.buffer.slice(0));
    const channel = audio.getChannelData(0);
    return resampleTo16k(channel, audio.sampleRate);
  } finally {
    ctx.close().catch(() => {});
  }
}

/**
 * Start a face-only Simli session into `video`.
 * Returns null when Simli is unset so the caller can keep TalkingHead.
 */
export async function startSimliFace({ edition, video, base, onStatus }) {
  const root = base || apiBase();
  const status = await simliStatus(edition, root);
  if (!status.enabled) {
    onStatus && onStatus(status);
    return null;
  }
  const res = await fetch(`${root}/avatar/simli/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ edition: edition || 'workroom' }),
  });
  const session = await res.json();
  if (!session.enabled || !session.session_token) {
    onStatus && onStatus(session);
    return null;
  }
  const pc = new RTCPeerConnection({
    iceServers: session.ice_servers && session.ice_servers.length
      ? session.ice_servers
      : [{ urls: 'stun:stun.l.google.com:19302' }],
  });
  pc.addTransceiver('video', { direction: 'recvonly' });
  pc.ontrack = (event) => {
    if (video && event.streams && event.streams[0]) {
      video.srcObject = event.streams[0];
      video.play().catch(() => {});
    }
  };
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  await new Promise((resolve) => {
    if (pc.iceGatheringState === 'complete') resolve();
    else {
      const timer = setTimeout(resolve, 1500);
      pc.addEventListener('icegatheringstatechange', () => {
        if (pc.iceGatheringState === 'complete') {
          clearTimeout(timer);
          resolve();
        }
      });
    }
  });
  const wsUrl = `${session.webrtc_url}?session_token=${encodeURIComponent(session.session_token)}`;
  const ws = new WebSocket(wsUrl);
  ws.binaryType = 'arraybuffer';
  const started = Date.now();
  let closed = false;
  const stop = (source) => {
    if (closed) return;
    closed = true;
    const seconds = Math.min(
      (Date.now() - started) / 1000,
      session.max_session_length || 600,
    );
    reportSimliMinutes(edition, seconds, source || 'simli', root);
    try { ws.close(); } catch { /* ignore */ }
    try { pc.close(); } catch { /* ignore */ }
  };
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Simli socket timed out')), 8000);
    ws.onopen = () => {
      clearTimeout(timer);
      ws.send(JSON.stringify({ type: 'offer', sdp: pc.localDescription.sdp }));
      resolve();
    };
    ws.onerror = () => {
      clearTimeout(timer);
      reject(new Error('Simli socket failed'));
    };
  });
  ws.onmessage = async (event) => {
    if (typeof event.data !== 'string') return;
    let msg;
    try { msg = JSON.parse(event.data); } catch { return; }
    if ((msg.type === 'answer' || msg.sdp) && msg.sdp) {
      await pc.setRemoteDescription({ type: 'answer', sdp: msg.sdp });
    }
  };
  ws.onclose = () => stop('simli');
  onStatus && onStatus({ ...status, renderer: 'simli', connected: true });
  return {
    renderer: 'simli',
    stop,
    sendPcm16(int16) {
      if (closed || ws.readyState !== WebSocket.OPEN || !int16) return;
      const bytes = int16 instanceof ArrayBuffer ? int16 : int16.buffer;
      ws.send(bytes);
    },
  };
}
