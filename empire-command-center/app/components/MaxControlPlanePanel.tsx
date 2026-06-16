'use client';

/**
 * MAX Control Plane Status Panel (2026-06-15 hotfix)
 *
 * This panel is the AUTHORITATIVE truth source for the Founder UI.
 * It separates MAX's IDENTITY (MAX) from its IMPLEMENTATION
 * (provider/model) and surfaces the live tool registry, local
 * broker, and memory freshness.
 *
 * Key design rules (from the 2026-06-15 hotfix):
 *  - MAX identity is shown as "MAX" (NOT as the provider/model).
 *  - Provider/model is shown SEPARATELY as an implementation detail.
 *  - Tools are shown with their proof_required flag.
 *  - Web/search is shown as "unavailable" if no backend is registered.
 *  - Handoff/startup mismatches are suppressed when the new
 *    /api/v1/max/memory-status endpoint reports `matches: true`.
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
    repo: { branch: string; commit: string };
    backend: { port: number; state: string; detail: string };
    frontend: { port: number; build_id: string; state: string };
  };
  tool_registry: Array<{
    key: string;
    status: string;
    proof_required: boolean;
    proof_reason: string;
    description: string;
  }>;
  memory: {
    handoff_freshness: { matches: boolean; warning: string | null };
    active_memory_source: string;
  };
  checked_at: string;
}

function statusTone(status: string): Tone {
  if (status === 'available' || status === 'up' || status === 'read-only') return 'ok';
  if (status === 'configured-but-unhealthy') return 'warn';
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
          tone={hf.matches ? 'ok' : 'warn'}
        />
        <Pill label={`Memory: ${data.memory.active_memory_source}`} tone="neutral" />
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
