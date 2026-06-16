'use client';

/**
 * MAX Control Plane Status Panel (2026-06-15 hotfix + 2026-06-15 proof-receipt patch)
 *
 * This panel is the AUTHORITATIVE truth source for the Founder UI.
 * It separates MAX's IDENTITY (MAX) from its IMPLEMENTATION
 * (provider/model) and surfaces the live tool registry, local
 * broker, and memory freshness.
 *
 * Key design rules (from the 2026-06-15 hotfix + patch):
 *  - MAX identity is shown as "MAX" (NOT as the provider/model).
 *  - Provider/model is shown SEPARATELY as an implementation detail.
 *  - Tools are shown with their proof_required flag.
 *  - Web/search is shown as "unavailable" if no backend is registered.
 *  - Handoff/startup mismatches are suppressed when the new
 *    /api/v1/max/memory-status endpoint reports `matches: true`.
 *  - OpenClaw queue detail is inlined in the local broker (not just
 *    a pointer to /api/v1/openclaw/health).
 *  - Memory timestamp + startup/current/runtime commit detail +
 *    warning text for stale are all displayed as text (not just
 *    chip status), per the 2026-06-15 proof-receipt patch.
 */

import { useEffect, useState } from 'react';
import { API } from '../lib/api';

type Tone = 'ok' | 'warn' | 'bad' | 'neutral';

function toneColor(tone: Tone) {
  if (tone === 'ok') return { bg: '#ecfdf5', fg: '#166534', border: '#bbf7d0' };
  if (tone === 'warn') return { bg: '#fffbeb', fg: '#92400e', border: '#fde68a' };
  if (tone === 'bad') return { bg: '#fef2f2', fg: '#991b1b', border: '#fecaca' };
  return { bg: '#f8fafc', fg: '#334155', border: '#e2e8f0' };
}

function Pill({ label, tone = 'neutral' }: { label: string; tone?: Tone }) {
  const c = toneColor(tone);
  return (
    <span style={{ border: `1px solid ${c.border}`, background: c.bg, color: c.fg, borderRadius: 8, padding: '3px 7px', fontSize: 11, fontWeight: 800, whiteSpace: 'nowrap' }}>
      {label}
    </span>
  );
}

interface ControlPlaneResponse {
  identity: {
    name: string;
    display_name: string;
    role: string;
    version: string;
  };
  provider: {
    provider_canonical?: string;
    model?: string;
    provider_label?: string;
    fallback_enabled?: boolean;
    ai_calls_disabled?: boolean;
    lane?: string;
    error?: string;
  };
  local_broker: {
    repo: { branch: string; commit: string; repo_root: string };
    backend: { port: number; state: string; detail: string };
    frontend: { port: number; build_id: string; state: string; detail: string };
    openclaw: {
      state: string;
      detail: string;
      queue_stats?: { queued: number | string; total: number | string };
      worker_heartbeat?: { state: string; age_seconds: number | string };
      proof_source?: string;
    };
    hermes: { state: string; detail: string; proof_source?: string };
    telegram: { state: string; detail: string; proof_source?: string };
    ollama: { state: string; detail: string; disabled_reason?: string };
  };
  tool_registry: Array<{
    key: string;
    status: string;
    proof_required: boolean;
    proof_reason: string;
    description: string;
  }>;
  memory: {
    handoff_freshness: {
      startup_commit: string;
      startup_recorded_at: string;
      current_commit: string;
      matches: boolean;
      warning: string | null;
    };
    active_memory_source: string;
    newest_memory_timestamp: string | null;
    newest_memory_file: string | null;
  };
  checked_at: string;
}

function statusTone(status: string): Tone {
  if (status === 'available' || status === 'up' || status === 'read-only') return 'ok';
  if (status === 'configured-but-unhealthy' || status === 'configured_but_detail_unavailable') return 'warn';
  if (status === 'unavailable' || status === 'down') return 'bad';
  return 'neutral';
}

export default function MaxControlPlanePanel() {
  const [data, setData] = useState<ControlPlaneResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(API + '/max/control-plane', { cache: 'no-store' });
      if (!res.ok) throw new Error('Control plane refresh failed.');
      setData(await res.json());
    } catch (exc: any) {
      setError(exc?.message || 'Control plane fetch failed.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (error && !data) {
    return (
      <section data-testid="max-control-plane-panel" style={{ border: '1px solid #fecaca', background: '#fef2f2', borderRadius: 8, padding: 12, color: '#991b1b' }}>
        <strong>MAX control plane unreachable.</strong> {error}
      </section>
    );
  }

  if (!data) {
    return (
      <section data-testid="max-control-plane-panel" style={{ border: '1px solid #e2e8f0', background: '#f8fafc', borderRadius: 8, padding: 12, color: '#334155' }}>
        Loading MAX control plane…
      </section>
    );
  }

  const hf = data.memory.handoff_freshness;
  const openclaw = data.local_broker.openclaw;
  const openclawQueue = openclaw.queue_stats;
  const openclawHeartbeat = openclaw.worker_heartbeat;
  const ocTone: Tone = openclaw.state === 'available' ? 'ok'
    : openclaw.state === 'configured_but_detail_unavailable' ? 'warn'
    : openclaw.state === 'unavailable' ? 'bad'
    : 'neutral';
  const hfTone: Tone = hf.matches ? 'ok' : 'warn';

  return (
    <section
      data-testid="max-control-plane-panel"
      style={{ border: '1px solid #d9ded5', background: '#fff', borderRadius: 8, padding: 12, fontFamily: "'Inter', 'Segoe UI', sans-serif" }}
    >
      <header style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 18, fontWeight: 900, color: '#171717' }} data-testid="cp-identity-name">
          {data.identity.display_name}
        </span>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>·</span>
        <span style={{ fontSize: 12, color: '#4d564d' }} data-testid="cp-identity-role">{data.identity.role}</span>
        <span style={{ marginLeft: 'auto' }}>
          <button
            data-testid="cp-refresh"
            onClick={load}
            disabled={loading}
            style={{ border: '1px solid #d8d3cb', background: '#fff', borderRadius: 8, padding: '4px 8px', fontSize: 11, fontWeight: 800, color: 'var(--text)', cursor: 'pointer' }}
          >
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </span>
      </header>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
        <Pill label={`Identity: ${data.identity.name}`} tone="ok" />
        <Pill
          label={`Provider: ${data.provider.provider_canonical || 'unknown'}${data.provider.fallback_enabled === false ? ' (no fallback)' : ''}`}
          tone="neutral"
        />
        <Pill label={`Model: ${data.provider.model || 'unknown'}`} tone="neutral" />
        {data.provider.lane && <Pill label={`Lane: ${data.provider.lane}`} tone="neutral" />}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
        <Pill label={`Repo ${data.local_broker.repo.branch}@${data.local_broker.repo.commit}`} tone="ok" />
        <Pill label={`Backend :${data.local_broker.backend.port} ${data.local_broker.backend.state}`} tone={statusTone(data.local_broker.backend.state)} />
        <Pill label={`Frontend :${data.local_broker.frontend.port} ${data.local_broker.frontend.state} (build ${data.local_broker.frontend.build_id})`} tone={statusTone(data.local_broker.frontend.state)} />
        <Pill
          label={hf.matches ? 'Handoff fresh' : 'Handoff stale'}
          tone={hfTone}
        />
        <Pill label={`Memory: ${data.memory.active_memory_source}`} tone="neutral" />
        <Pill
          label={`OpenClaw ${openclawQueue ? `q=${openclawQueue.queued}/${openclawQueue.total}` : 'no detail'}`}
          tone={ocTone}
        />
      </div>

      {/* Per the 2026-06-15 patch: show full warning text + memory timestamp + commit detail */}
      {hf.warning && (
        <div
          data-testid="cp-handoff-warning"
          style={{
            fontSize: 12,
            fontWeight: 700,
            color: '#92400e',
            background: '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: 6,
            padding: '6px 8px',
            marginBottom: 8,
          }}
        >
          ⚠ {hf.warning}
        </div>
      )}

      <div
        data-testid="cp-commit-detail"
        style={{
          fontSize: 11,
          color: '#4d564d',
          fontFamily: 'monospace',
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: 6,
          padding: '6px 8px',
          marginBottom: 8,
        }}
      >
        <div><strong>startup_commit:</strong> {hf.startup_commit || 'unknown'}</div>
        <div><strong>startup_recorded_at:</strong> {hf.startup_recorded_at || 'unknown'}</div>
        <div><strong>current_commit:</strong> {hf.current_commit || 'unknown'}</div>
        <div><strong>matches:</strong> {hf.matches ? 'true' : 'false'}</div>
        {data.memory.newest_memory_timestamp && (
          <div data-testid="cp-newest-memory-timestamp"><strong>newest_memory_timestamp:</strong> {data.memory.newest_memory_timestamp}</div>
        )}
        {data.memory.newest_memory_file && (
          <div><strong>newest_memory_file:</strong> {data.memory.newest_memory_file}</div>
        )}
      </div>

      <details>
        <summary style={{ cursor: 'pointer', fontSize: 12, fontWeight: 800, color: '#4d564d', padding: '4px 0' }}>
          Tool registry ({data.tool_registry.length} tools)
        </summary>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
          {data.tool_registry.map((tool) => (
            <div key={tool.key} data-testid={`cp-tool-${tool.key}`} style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 11, fontWeight: 800, color: '#171717', minWidth: 110 }}>{tool.key}</span>
              <Pill label={tool.status} tone={statusTone(tool.status)} />
              {tool.proof_required && <Pill label="proof_required" tone="neutral" />}
              <span style={{ fontSize: 10, color: '#4d564d', fontFamily: 'monospace' }}>{tool.proof_reason}</span>
            </div>
          ))}
        </div>
      </details>

      <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 8 }}>
        Checked at {data.checked_at} · {data.identity.version}
      </div>
    </section>
  );
}
