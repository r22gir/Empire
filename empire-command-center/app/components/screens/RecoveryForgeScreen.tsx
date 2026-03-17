'use client';
import { useState, useEffect, useCallback } from 'react';
import { HardDrive, Play, Square, RefreshCw, Loader2 } from 'lucide-react';
import { API } from '../../lib/api';

interface RecoveryStatus {
  total_images: number;
  processed: number;
  percentage: number;
  running: boolean;
  categories: Record<string, number>;
}

export default function RecoveryForgeScreen() {
  const [status, setStatus] = useState<RecoveryStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [serviceUp, setServiceUp] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/recovery/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch {
      // API might be down
    }

    // Check if RecoveryForge web UI is up
    try {
      const res = await fetch('http://localhost:3077', { signal: AbortSignal.timeout(3000) });
      setServiceUp(res.ok || res.status === 404);
    } catch {
      setServiceUp(false);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleAction = async (action: 'start' | 'stop') => {
    setActionLoading(true);
    try {
      await fetch(`${API}/recovery/${action}`, { method: 'POST' });
      setTimeout(fetchStatus, 2000);
    } catch (e) {
      console.error('Action failed:', e);
    }
    setActionLoading(false);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin" size={20} style={{ color: '#b8960c' }} />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header + Status Bar */}
      <div style={{
        padding: '12px 20px',
        background: '#faf9f7',
        borderBottom: '1px solid #ece8e0',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexShrink: 0,
      }}>
        <HardDrive size={20} style={{ color: '#b8960c' }} />
        <h2 style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>
          RecoveryForge — Layer 3 File Recovery
        </h2>

        {status && (
          <>
            <div style={{
              marginLeft: 'auto',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              fontSize: 12,
              color: '#666',
            }}>
              <span style={{
                padding: '3px 10px',
                borderRadius: 20,
                fontSize: 11,
                fontWeight: 600,
                background: status.running ? '#dcfce7' : '#fef2f2',
                color: status.running ? '#16a34a' : '#dc2626',
              }}>
                {status.running ? 'Running' : 'Stopped'}
              </span>
              <span>{status.processed.toLocaleString()} / {status.total_images.toLocaleString()} images ({status.percentage}%)</span>
            </div>

            <button
              onClick={() => handleAction(status.running ? 'stop' : 'start')}
              disabled={actionLoading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 14px',
                borderRadius: 8,
                border: 'none',
                background: status.running ? '#dc2626' : '#16a34a',
                color: '#fff',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                opacity: actionLoading ? 0.6 : 1,
              }}
            >
              {actionLoading ? <Loader2 size={14} className="animate-spin" /> :
                status.running ? <Square size={14} /> : <Play size={14} />}
              {status.running ? 'Stop' : 'Start'}
            </button>
          </>
        )}

        <button
          onClick={fetchStatus}
          style={{
            background: 'none',
            border: '1px solid #ece8e0',
            borderRadius: 8,
            padding: '6px 10px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <RefreshCw size={14} style={{ color: '#999' }} />
        </button>
      </div>

      {/* Iframe or Fallback */}
      <div style={{ flex: 1, position: 'relative' }}>
        {serviceUp ? (
          <iframe
            src="http://localhost:3077"
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              WebkitOverflowScrolling: 'touch' as any,
            }}
            title="RecoveryForge"
            allow="fullscreen"
          />
        ) : (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            gap: 16,
            color: '#999',
          }}>
            <HardDrive size={48} style={{ color: '#ddd' }} />
            <div style={{ fontSize: 16, fontWeight: 600, color: '#666' }}>
              RecoveryForge service not running
            </div>
            <div style={{ fontSize: 13, color: '#999' }}>
              Start the service on port 3077 to view the web UI here.
            </div>
            <button
              onClick={() => handleAction('start')}
              disabled={actionLoading}
              style={{
                padding: '10px 24px',
                borderRadius: 10,
                border: 'none',
                background: '#b8960c',
                color: '#fff',
                fontSize: 14,
                fontWeight: 700,
                cursor: 'pointer',
                minHeight: 44,
              }}
            >
              {actionLoading ? 'Starting...' : 'Start RecoveryForge'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
