'use client';

import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Loader } from 'lucide-react';

type Status = 'pending' | 'running' | 'done' | 'error';

interface InstallPhase {
  id: string;
  label: string;
  status: Status;
  detail?: string;
}

interface Props {
  state: {
    accountEmail: string;
    accountToken: string;
    licenseKey: string;
    selectedProducts: string[];
    selectedModels: string[];
  };
  deviceId: string;
  onPrev: () => void;
}

export default function InstallStep({ state, deviceId, onPrev }: Props) {
  const [phases, setPhases] = useState<InstallPhase[]>([
    { id: 'connect',  label: 'Connecting to device',          status: 'pending' },
    { id: 'system',   label: 'Updating system packages',      status: 'pending' },
    { id: 'docker',   label: 'Installing Docker',             status: 'pending' },
    { id: 'products', label: `Installing products (${state.selectedProducts.length})`, status: 'pending' },
    { id: 'ollama',   label: `Downloading AI models (${state.selectedModels.length})`, status: 'pending' },
    { id: 'start',    label: 'Starting all services',         status: 'pending' },
    { id: 'complete', label: 'Setup complete',                status: 'pending' },
  ]);
  const [overall, setOverall] = useState<'running' | 'done' | 'error'>('running');
  const [logs, setLogs] = useState<string[]>(['Starting EmpireBox setup...']);

  const setPhaseStatus = (id: string, status: Status, detail?: string) => {
    setPhases((prev) =>
      prev.map((p) => (p.id === id ? { ...p, status, detail } : p))
    );
  };

  const addLog = (line: string) => setLogs((l) => [...l, line]);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      // Simulate installation phases (in production, this drives a real WebSocket)
      const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

      const steps: Array<{ id: string; ms: number; log: string }> = [
        { id: 'connect',  ms: 1000, log: `Connected to device ${deviceId}` },
        { id: 'system',   ms: 2000, log: 'System packages updated' },
        { id: 'docker',   ms: 2500, log: 'Docker installed and started' },
        { id: 'products', ms: 4000, log: `Installed: ${state.selectedProducts.join(', ')}` },
        { id: 'ollama',   ms: 3000, log: `Models downloaded: ${state.selectedModels.join(', ')}` },
        { id: 'start',    ms: 1500, log: 'All services started' },
        { id: 'complete', ms: 500,  log: 'Setup complete!' },
      ];

      for (const s of steps) {
        if (cancelled) return;
        setPhaseStatus(s.id, 'running');
        await delay(s.ms);
        if (cancelled) return;
        setPhaseStatus(s.id, 'done');
        addLog(s.log);
      }

      setOverall('done');
    };

    run().catch((err) => {
      addLog(`Error: ${err instanceof Error ? err.message : String(err)}`);
      setOverall('error');
    });

    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h2 className="text-xl font-semibold mb-1">Installing</h2>
      <p className="text-gray-400 mb-6 text-sm">
        {overall === 'done' ? 'Setup complete! 🎉' : overall === 'error' ? 'Setup encountered an error' : 'Please wait while EmpireBox is configured…'}
      </p>

      <div className="space-y-2 mb-6">
        {phases.map((p) => (
          <div key={p.id} className="flex items-center gap-3 text-sm">
            <div className="w-5 h-5 flex-shrink-0">
              {p.status === 'done' && <CheckCircle size={20} style={{ color: '#C9A84C' }} />}
              {p.status === 'error' && <XCircle size={20} className="text-red-400" />}
              {p.status === 'running' && <Loader size={20} className="text-white animate-spin" />}
              {p.status === 'pending' && <div className="w-5 h-5 rounded-full border border-white/20" />}
            </div>
            <span className={p.status === 'pending' ? 'text-gray-500' : 'text-white'}>{p.label}</span>
            {p.detail && <span className="text-gray-500 text-xs">{p.detail}</span>}
          </div>
        ))}
      </div>

      {/* Log output */}
      <div className="bg-black/40 rounded-lg p-3 font-mono text-xs text-green-400 h-28 overflow-y-auto mb-4">
        {logs.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </div>

      {overall === 'done' && (
        <div className="text-center p-4 rounded-lg" style={{ backgroundColor: '#C9A84C22', borderColor: '#C9A84C', border: '1px solid' }}>
          <p className="font-semibold" style={{ color: '#C9A84C' }}>Your EmpireBox is ready!</p>
          <p className="text-gray-400 text-sm mt-1">Access your apps at http://EmpireBox-{deviceId}.local</p>
        </div>
      )}

      {overall === 'error' && (
        <button onClick={onPrev} className="w-full py-3 rounded-lg bg-white/10 text-white font-medium">
          Back
        </button>
      )}
    </div>
  );
}
