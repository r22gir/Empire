'use client';
import { useState, useEffect, useCallback } from 'react';
import { QrCode, Smartphone, Copy, RefreshCw, Power, PowerOff, Loader2, CheckCircle, XCircle, ExternalLink } from 'lucide-react';

const QR_API = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/qr`;

interface PairingStatus {
  status: 'running' | 'stopped' | 'starting' | 'stopping';
  url: string | null;
  port: number;
  local_ip: string | null;
}

interface StartResult extends PairingStatus {
  qr_preview?: string;
}

export default function DesktopPairing() {
  const [status, setStatus] = useState<PairingStatus | null>(null);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${QR_API}/pairing/status`);
      const d = await r.json();
      setStatus(d);
      setError(null);
    } catch {
      setError('Cannot reach backend');
    }
  }, []);

  const startPairing = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${QR_API}/pairing/start`, { method: 'POST' });
      const d: StartResult = await r.json();
      setStatus(d);
      if (d.qr_preview) {
        setQrUrl(d.qr_preview);
      } else if (d.status === 'running') {
        setQrUrl(`${QR_API}/pairing/qr?_=${Date.now()}`);
      }
    } catch {
      setError('Failed to start pairing server');
    }
    setLoading(false);
  }, []);

  const stopPairing = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await fetch(`${QR_API}/pairing/stop`, { method: 'POST' });
      setStatus({ status: 'stopped', url: null, port: 8787, local_ip: null });
      setQrUrl(null);
    } catch {
      setError('Failed to stop pairing server');
    }
    setLoading(false);
  }, []);

  const copyLink = useCallback(async () => {
    if (!status?.url) return;
    try {
      await navigator.clipboard.writeText(status.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [status]);

  const refreshQr = useCallback(() => {
    if (status?.status === 'running') {
      setQrUrl(`${QR_API}/pairing/qr?_=${Date.now()}`);
    }
  }, [status]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const isRunning = status?.status === 'running';
  const isTransitioning = status?.status === 'starting' || status?.status === 'stopping';

  return (
    <div style={{
      background: '#fff',
      border: '1px solid #e5e2dc',
      borderRadius: 12,
      padding: 24,
      marginBottom: 16,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <Smartphone size={20} style={{ color: '#06b6d4' }} />
        <span style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>OpenCode Phone Pairing</span>
        <span style={{
          marginLeft: 'auto',
          display: 'flex', alignItems: 'center', gap: 5,
          fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 12,
          background: isRunning ? '#f0fdf4' : '#f5f3ef',
          color: isRunning ? '#16a34a' : '#888',
        }}>
          {isTransitioning || loading ? (
            <><Loader2 size={10} className="animate-spin" /> {status?.status || 'loading'}</>
          ) : isRunning ? (
            <><CheckCircle size={10} /> Active</>
          ) : (
            <><XCircle size={10} /> Inactive</>
          )}
        </span>
      </div>

      <p style={{ fontSize: 12, color: '#666', marginBottom: 16, marginTop: 0 }}>
        Start the OpenCode ACP server to pair your phone. Scan the QR code on your phone&apos;s OpenCode app to connect.
      </p>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '8px 12px', fontSize: 12, color: '#dc2626', marginBottom: 12 }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        {!isRunning ? (
          <button
            onClick={startPairing}
            disabled={loading || isTransitioning}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8,
              background: '#06b6d4', color: '#fff', border: 'none',
              fontSize: 12, fontWeight: 600, cursor: loading ? 'wait' : 'pointer',
            }}
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <Power size={12} />}
            Start Pairing Server
          </button>
        ) : (
          <button
            onClick={stopPairing}
            disabled={loading || isTransitioning}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8,
              background: '#f5f3ef', color: '#666', border: '1px solid #e5e2dc',
              fontSize: 12, fontWeight: 600, cursor: loading ? 'wait' : 'pointer',
            }}
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <PowerOff size={12} />}
            Stop Server
          </button>
        )}

        {isRunning && (
          <button
            onClick={refreshQr}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8,
              background: '#f5f3ef', color: '#666', border: '1px solid #e5e2dc',
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
            }}
          >
            <RefreshCw size={12} />
            Refresh QR
          </button>
        )}

        {isRunning && (
          <button
            onClick={copyLink}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8,
              background: '#f5f3ef', color: '#666', border: '1px solid #e5e2dc',
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
            }}
          >
            {copied ? <CheckCircle size={12} style={{ color: '#16a34a' }} /> : <Copy size={12} />}
            {copied ? 'Copied!' : 'Copy Link'}
          </button>
        )}
      </div>

      {isRunning && (qrUrl || status?.url) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{
            background: '#fff',
            border: '2px solid #e5e2dc',
            borderRadius: 12,
            padding: 12,
            display: 'inline-block',
          }}>
            {qrUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={qrUrl} alt="Pairing QR Code" style={{ width: 180, height: 180, display: 'block' }} />
            ) : (
              <div style={{ width: 180, height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f3ef', borderRadius: 8 }}>
                <Loader2 size={24} className="animate-spin" style={{ color: '#06b6d4' }} />
              </div>
            )}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>Pairing URL</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', fontFamily: 'monospace', wordBreak: 'break-all' }}>
              {status?.url}
            </div>
            <div style={{ fontSize: 11, color: '#aaa', marginTop: 6 }}>
              Open the OpenCode app on your phone and scan this QR code, or visit the URL directly.
            </div>
          </div>
        </div>
      )}

      {!isRunning && (
        <div style={{
          background: '#f5f3ef',
          borderRadius: 10,
          padding: 20,
          textAlign: 'center',
          color: '#999',
          fontSize: 12,
        }}>
          <QrCode size={32} style={{ marginBottom: 8, opacity: 0.3 }} />
          <div>Server is stopped. Click &quot;Start Pairing Server&quot; to begin.</div>
        </div>
      )}
    </div>
  );
}
