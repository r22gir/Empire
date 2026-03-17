'use client';
import { useState, useEffect, useCallback } from 'react';
import { ShoppingBag, RefreshCw, Loader2 } from 'lucide-react';

export default function RelistAppScreen() {
  const [serviceUp, setServiceUp] = useState(false);
  const [loading, setLoading] = useState(true);

  const checkService = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:3007', { signal: AbortSignal.timeout(3000) });
      setServiceUp(res.ok || res.status === 404 || res.status === 307);
    } catch {
      setServiceUp(false);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    checkService();
    const interval = setInterval(checkService, 30000);
    return () => clearInterval(interval);
  }, [checkService]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin" size={20} style={{ color: '#b8960c' }} />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 px-4 sm:px-5 py-3" style={{
        background: '#faf9f7',
        borderBottom: '1px solid #ece8e0',
        flexShrink: 0,
      }}>
        <ShoppingBag size={20} style={{ color: '#b8960c' }} />
        <h2 className="text-sm sm:text-base" style={{ fontWeight: 700, color: '#1a1a1a', margin: 0 }}>
          RelistApp — Smart Lister
        </h2>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            padding: '3px 10px',
            borderRadius: 20,
            fontSize: 11,
            fontWeight: 600,
            background: serviceUp ? '#dcfce7' : '#fef2f2',
            color: serviceUp ? '#16a34a' : '#dc2626',
          }}>
            {serviceUp ? 'Running' : 'Offline'}
          </span>
          <button
            onClick={checkService}
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
      </div>

      {/* Iframe or Fallback */}
      <div style={{ flex: 1, position: 'relative' }}>
        {serviceUp ? (
          <iframe
            src="http://localhost:3007"
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              WebkitOverflowScrolling: 'touch' as any,
            }}
            title="RelistApp"
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
            <ShoppingBag size={48} style={{ color: '#ddd' }} />
            <div style={{ fontSize: 16, fontWeight: 600, color: '#666' }}>
              RelistApp service not running
            </div>
            <div style={{ fontSize: 13, color: '#999' }}>
              Start RelistApp on port 3007 to view it here.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
