'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../lib/api';
import {
  RefreshCw, Play, Square, RotateCw, AlertCircle, CheckCircle2,
  XCircle, Server, Globe, Bot, Cpu, HardDrive, Shield, Terminal
} from 'lucide-react';

interface ServiceStatus {
  status: 'online' | 'offline' | 'unknown';
  port: number | null;
  pid: number | null;
  conflict_pid?: number;
  error?: string;
  hint?: string;
}

const SERVICES = [
  { key: 'v10_backend', label: 'v10 Backend', port: 8010, icon: <Server size={16} /> },
  { key: 'v10_frontend', label: 'v10 Frontend', port: 3010, icon: <Globe size={16} /> },
  { key: 'stable_backend', label: 'Stable Backend', port: 8000, icon: <Server size={16} /> },
  { key: 'stable_frontend', label: 'Stable Frontend', port: 3005, icon: <Globe size={16} /> },
  { key: 'openclaw', label: 'OpenClaw', port: 7878, icon: <Cpu size={16} /> },
  { key: 'telegram_bot', label: 'Telegram Bot', port: null, icon: <Bot size={16} /> },
  { key: 'cloudflare_tunnel', label: 'Cloudflare Tunnel', port: null, icon: <Globe size={16} /> },
  { key: 'ollama', label: 'Ollama', port: 11434, icon: <Cpu size={16} /> },
];

export default function SystemAdminScreen() {
  const [services, setServices] = useState<Record<string, ServiceStatus>>({});
  const [loading, setLoading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [conflictModal, setConflictModal] = useState<{ service: string; port: number; conflict_pid: number } | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/admin/services?_=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        setServices(data);
      }
    } catch (e) {
      console.error('Failed to fetch service status:', e);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleAction = async (name: string, action: 'start' | 'stop' | 'restart', force = false) => {
    setActionInProgress(name);
    try {
      const res = await fetch(`${API}/admin/services/${name}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force }),
      });
      const data = await res.json();

      if (res.status === 409) {
        // Port conflict
        setConflictModal({
          service: name,
          port: data.detail?.port || 0,
          conflict_pid: data.detail?.conflict_pid,
        });
      } else if (!res.ok) {
        alert(`Error: ${JSON.stringify(data)}`);
      }

      await fetchStatus();
    } catch (e) {
      console.error(`Failed to ${action} ${name}:`, e);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleForceStart = async () => {
    if (!conflictModal) return;
    await handleAction(conflictModal.service, 'start', true);
    setConflictModal(null);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'online': return <CheckCircle2 size={14} className="text-green-400" />;
      case 'offline': return <XCircle size={14} className="text-red-400" />;
      default: return <AlertCircle size={14} className="text-yellow-400" />;
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Terminal size={24} className="text-empire-accent" />
          <h1 className="text-2xl font-bold">System Admin</h1>
        </div>
        <button
          onClick={fetchStatus}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-empire-surface hover:bg-empire-surface-elevated transition-colors"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Service Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SERVICES.map(({ key, label, port, icon }) => {
          const svc = services[key] || { status: 'unknown', port, pid: null };
          const isOnline = svc.status === 'online';
          const busy = actionInProgress === key;

          return (
            <div
              key={key}
              className="border border-empire-border rounded-lg p-4 bg-empire-surface-elevated"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {icon}
                  <span className="font-medium text-sm">{label}</span>
                </div>
                <div className="flex items-center gap-1">
                  {getStatusIcon(svc.status)}
                  <span className="text-xs ml-1">{svc.status}</span>
                </div>
              </div>

              <div className="flex gap-1.5 mb-2">
                <button
                  onClick={() => handleAction(key, 'start')}
                  disabled={isOnline || busy}
                  className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium bg-green-600/20 text-green-400 hover:bg-green-600/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <Play size={12} /> Start
                </button>
                <button
                  onClick={() => handleAction(key, 'stop')}
                  disabled={!isOnline || busy}
                  className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium bg-red-600/20 text-red-400 hover:bg-red-600/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <Square size={12} /> Stop
                </button>
                <button
                  onClick={() => handleAction(key, 'restart')}
                  disabled={busy}
                  className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium bg-yellow-600/20 text-yellow-400 hover:bg-yellow-600/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <RotateCw size={12} /> Restart
                </button>
              </div>

              <div className="flex justify-between text-xs text-empire-text-muted">
                {port ? <span>Port: {port}</span> : <span>No port</span>}
                {svc.pid ? <span>PID: {svc.pid}</span> : <span>PID: —</span>}
              </div>

              {busy && (
                <div className="mt-2 text-xs text-empire-accent animate-pulse">
                  Processing...
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Conflict Resolution Modal */}
      {conflictModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-empire-surface-elevated border border-empire-border rounded-lg p-6 max-w-sm w-full">
            <div className="flex items-center gap-2 mb-4">
              <AlertCircle size={20} className="text-yellow-400" />
              <h3 className="text-lg font-semibold">Port Conflict</h3>
            </div>
            <p className="text-sm text-empire-text-muted mb-4">
              Port <span className="font-mono text-white">{conflictModal.port}</span> is already in use by PID{' '}
              <span className="font-mono text-white">{conflictModal.conflict_pid}</span>.
            </p>
            <p className="text-xs text-empire-text-muted mb-4">
              Do you want to kill the conflicting process and start {conflictModal.service}?
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleForceStart}
                className="flex-1 px-3 py-2 rounded bg-red-600 hover:bg-red-700 text-sm font-medium transition-colors"
              >
                Kill & Start
              </button>
              <button
                onClick={() => setConflictModal(null)}
                className="flex-1 px-3 py-2 rounded bg-empire-surface hover:bg-empire-border text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
