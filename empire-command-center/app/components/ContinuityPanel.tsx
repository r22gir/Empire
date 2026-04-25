'use client';

import { useEffect, useMemo, useState } from 'react';
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

function field(label: string, value: any) {
  return (
    <div>
      <div style={{ fontSize: 10, textTransform: 'uppercase', fontWeight: 900, color: 'var(--muted)' }}>{label}</div>
      <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value ?? 'unknown'}</div>
    </div>
  );
}

function checkedAtLabel(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

interface ContinuityPanelProps {
  mode?: 'compact' | 'full';
  onOpenContinuity?: () => void;
}

export default function ContinuityPanel({ mode = 'full', onOpenContinuity }: ContinuityPanelProps) {
  const [status, setStatus] = useState<any>(null);
  const [audit, setAudit] = useState<any>(null);
  const [openclawHealth, setOpenclawHealth] = useState<any>(null);
  const [scores, setScores] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(mode === 'full');
  const loading = pendingAction !== null;

  const load = async (runAudit = true) => {
    const [statusRes, scoresRes] = await Promise.all([
      fetch(API + '/max/status', { cache: 'no-store' }),
      fetch(API + '/max/evaluation/scores?limit=5', { cache: 'no-store' }),
    ]);
    if (!statusRes.ok) throw new Error('MAX status refresh failed.');
    setStatus(await statusRes.json());
    if (scoresRes.ok) setScores((await scoresRes.json()).scores || []);
    if (runAudit) {
      const auditRes = await fetch(API + '/max/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'what continuity packet is loaded', model: 'auto', history: [], channel: 'web' }),
      });
      if (auditRes.ok) setAudit(await auditRes.json());
    }
    setLastCheckedAt(checkedAtLabel());
  };

  useEffect(() => {
    load().catch(() => {});
  }, []);

  const auditResult = audit?.tool_results?.[0]?.result || {};
  const handoff = auditResult?.handoff || {};
  const tier1 = handoff?.tier_1 || {};
  const runtime = tier1?.last_runtime_truth_result || {};
  const gate = openclawHealth?.openclaw_gate || status?.openclaw_gate || runtime?.openclaw_gate || {};
  const heartbeat = gate?.worker_heartbeat || {};
  const currentCommit = status?.current_commit?.hash;
  const handoffCommit = runtime?.commit;
  const startupCommit = status?.startup_health?.running_commit_hash;
  const handoffCommitDiffers = Boolean(currentCommit && handoffCommit && handoffCommit !== currentCommit);
  const startupCommitDiffers = Boolean(currentCommit && startupCommit && startupCommit !== currentCommit);
  const staleCommitWarning = Boolean(handoffCommitDiffers || startupCommitDiffers);
  const latestScore = scores[0]?.overall_score ?? auditResult?.latest_score?.overall_score;
  const avgScore = useMemo(() => {
    if (!scores.length) return null;
    return scores.reduce((sum, item) => sum + Number(item.overall_score || 0), 0) / scores.length;
  }, [scores]);
  const skillInvocations = scores.filter(s => s.skill_used).slice(0, 5);
  const gateTone: Tone = gate.state === 'healthy' ? 'ok' : gate.state === 'degraded' ? 'warn' : gate.state === 'unavailable' ? 'bad' : 'warn';
  const heartbeatTone: Tone = heartbeat.state === 'fresh' ? 'ok' : heartbeat.state === 'stale' ? 'bad' : 'warn';
  const registryTone: Tone = !status?.registry?.registry_version || status?.registry?.last_error || status?.registry_reload_requires_restart ? 'bad' : 'ok';
  const scoreTone: Tone = Number(latestScore ?? 1) < 0.6 ? 'warn' : 'ok';
  const registryLabel = registryTone === 'ok' ? 'Registry OK' : `Registry ${status?.registry?.registry_version || 'unknown'}`;
  const handoffLabel = runtime.restart_required === undefined
    ? 'Handoff unknown'
    : runtime.restart_required
      ? 'Handoff restart needed'
      : 'Handoff fresh';
  const compactHandoffLabel = handoffCommitDiffers
    ? `Handoff stale ${handoffCommit}`
    : handoffLabel;

  const runCommand = async (command: string, successLabel: string) => {
    const checkedAt = checkedAtLabel();
    setPendingAction(command === 'what continuity packet is loaded' ? 'audit' : 'save');
    setMessage('');
    try {
      const res = await fetch(API + '/max/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: command, model: 'auto', history: [], channel: 'web' }),
      });
      if (!res.ok) throw new Error(`${successLabel} failed.`);
      const data = await res.json();
      setMessage(`${data.response || successLabel}\nChecked at ${checkedAt}.`);
      if (command === 'what continuity packet is loaded') setAudit(data);
      await load(command !== 'what continuity packet is loaded');
      setLastCheckedAt(checkedAt);
    } catch (exc: any) {
      setMessage(`${exc?.message || 'Continuity action failed.'}\nChecked at ${checkedAt}.`);
    } finally {
      setPendingAction(null);
    }
  };

  const refreshOpenclawStatus = async () => {
    const checkedAt = checkedAtLabel();
    setPendingAction('openclaw');
    setMessage('');
    try {
      const [statusRes, scoresRes, healthRes] = await Promise.all([
        fetch(API + '/max/status', { cache: 'no-store' }),
        fetch(API + '/max/evaluation/scores?limit=5', { cache: 'no-store' }),
        fetch(API + '/openclaw/health', { cache: 'no-store' }),
      ]);
      if (!statusRes.ok) throw new Error('MAX status refresh failed.');
      if (!healthRes.ok) throw new Error('OpenClaw health check failed.');
      const statusData = await statusRes.json();
      const healthData = await healthRes.json();
      setStatus(statusData);
      setOpenclawHealth(healthData);
      if (scoresRes.ok) setScores((await scoresRes.json()).scores || []);
      const gateState = healthData?.openclaw_gate?.state || statusData?.openclaw_gate?.state || healthData?.status || 'unknown';
      setMessage(`OpenClaw status refreshed at ${checkedAt}: ${gateState}.`);
      setLastCheckedAt(checkedAt);
    } catch (exc: any) {
      setMessage(`${exc?.message || 'OpenClaw status refresh failed.'}\nChecked at ${checkedAt}.`);
    } finally {
      setPendingAction(null);
    }
  };

  if (mode === 'compact') {
    return (
      <section
        data-testid="max-continuity-strip"
        className="continuity-strip"
        style={{
          flexShrink: 0,
          borderBottom: '1px solid var(--border)',
          background: staleCommitWarning ? '#fffbeb' : '#fff',
          padding: '6px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          overflowX: 'auto',
          whiteSpace: 'nowrap',
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 900, color: staleCommitWarning ? '#92400e' : 'var(--text)' }}>
          MAX Truth:
        </span>
        <Pill label={registryLabel} tone={registryTone} />
        <Pill label={`Commit ${currentCommit || 'unknown'}`} tone={currentCommit ? 'ok' : 'warn'} />
        <Pill label={`OpenClaw ${gate.state || 'unknown'}`} tone={gateTone} />
        <Pill label={compactHandoffLabel} tone={staleCommitWarning || runtime.restart_required ? 'warn' : runtime.restart_required === undefined ? 'neutral' : 'ok'} />
        <Pill label={`Worker ${heartbeat.state || 'unknown'}${Number.isFinite(heartbeat.age_seconds) ? ` ${heartbeat.age_seconds}s` : ''}`} tone={heartbeatTone} />
        {lastCheckedAt && <Pill label={`Checked ${lastCheckedAt}`} tone="neutral" />}
        {startupCommitDiffers && <Pill label={`Startup ${startupCommit} differs`} tone="warn" />}
        {staleCommitWarning && currentCommit && (
          <span style={{ color: '#92400e', fontSize: 11, fontWeight: 800 }}>
            Live truth wins.
          </span>
        )}
        <button
          data-testid="continuity-open-full"
          onClick={onOpenContinuity}
          style={{
            marginLeft: 'auto',
            border: '1px solid #d8d3cb',
            background: '#fff',
            borderRadius: 8,
            padding: '4px 8px',
            fontSize: 11,
            fontWeight: 800,
            color: 'var(--text)',
            cursor: 'pointer',
            flexShrink: 0,
          }}
        >
          Open Continuity
        </button>
      </section>
    );
  }

  return (
    <section data-testid="max-continuity-panel" className="continuity-panel" style={{ flexShrink: 0, borderBottom: '1px solid var(--border)', background: '#fff', padding: '10px 12px' }}>
      <div className="continuity-head" style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 11, fontWeight: 900, color: 'var(--muted)', textTransform: 'uppercase' }}>MAX Continuity</div>
          <div className="continuity-chips" style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 5 }}>
            <Pill label={`Registry ${status?.registry?.registry_version || 'unknown'}`} tone={registryTone} />
            <Pill label={`Eval ${latestScore ?? 'none'}`} tone={scoreTone} />
            <Pill label={`OpenClaw ${gate.state || 'unknown'}`} tone={gateTone} />
            <Pill label={`Worker ${heartbeat.state || 'unknown'}${Number.isFinite(heartbeat.age_seconds) ? ` ${heartbeat.age_seconds}s` : ''}`} tone={heartbeatTone} />
            {lastCheckedAt && <Pill label={`Checked ${lastCheckedAt}`} tone="neutral" />}
          </div>
        </div>
        <div className="continuity-actions" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button data-testid="continuity-toggle-details" onClick={() => setExpanded(v => !v)} style={buttonStyle}>{expanded ? 'Hide' : 'Details'}</button>
          <button data-testid="continuity-save-state" disabled={loading} onClick={() => runCommand('save state', 'State saved')} style={buttonStyle}>Save State</button>
          <button data-testid="continuity-run-audit" disabled={loading} onClick={() => runCommand('what continuity packet is loaded', 'Audit complete')} style={buttonStyle}>{pendingAction === 'audit' ? 'Running...' : 'Run Continuity Audit'}</button>
          <button data-testid="continuity-check-openclaw" disabled={loading} onClick={refreshOpenclawStatus} style={buttonStyle}>{pendingAction === 'openclaw' ? 'Refreshing...' : 'Refresh OpenClaw Status'}</button>
        </div>
      </div>

      <div className={expanded ? 'continuity-details expanded' : 'continuity-details'} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10, marginTop: 10 }}>
        {field('current task', tier1.current_task)}
        {field('surface', tier1.founder_surface_identity?.canonical_channel || auditResult.surface?.canonical_channel)}
        {field('current commit', currentCommit)}
        {handoffCommit && field('handoff commit', handoffCommitDiffers ? `${handoffCommit} (stale)` : handoffCommit)}
        {startupCommit && field('startup commit', startupCommitDiffers ? `${startupCommit} (differs from current)` : startupCommit)}
        {field('handoff truth', runtime.restart_required === undefined ? 'unknown' : runtime.restart_required ? 'restart needed' : 'fresh')}
        {field('5-score trend', avgScore === null ? 'none' : `${avgScore.toFixed(2)} ${avgScore < 0.6 ? 'down' : 'stable'}`)}
        {field('active skills', (status?.active_skill_hooks || []).join(', ') || 'none')}
      </div>

      <div className={expanded ? 'continuity-extra expanded' : 'continuity-extra'} style={{ marginTop: 10, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(220px, 360px)', gap: 12 }}>
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>
          {staleCommitWarning && currentCommit && (
            <div style={{ color: '#92400e', fontWeight: 700, marginBottom: 6 }}>
              Continuity packet/startup truth is stale; live backend reports current commit {currentCommit}.
            </div>
          )}
          <div style={{ whiteSpace: 'pre-wrap' }}>{message || 'Use this panel to refresh handoff state, audit continuity, and check OpenClaw gate truth.'}</div>
        </div>
        <div data-testid="continuity-skill-invocations" style={{ fontSize: 11, color: 'var(--muted)' }}>
          <strong style={{ color: 'var(--text)' }}>Recent skill invocations</strong>
          {skillInvocations.length === 0 && <div>No scored skill invocations yet.</div>}
          {skillInvocations.map(item => (
            <div key={`${item.source}-${item.source_id}`} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {item.skill_used} · {item.overall_score} · {item.scored_at}
            </div>
          ))}
        </div>
      </div>
      <style jsx>{`
        @media (max-width: 700px) {
          .continuity-panel {
            padding: 8px 10px !important;
            max-height: 190px;
            overflow-y: auto;
          }
          .continuity-head {
            align-items: flex-start !important;
            gap: 8px !important;
          }
          .continuity-chips {
            max-width: 100%;
          }
          .continuity-actions {
            width: 100%;
            display: grid !important;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 6px !important;
          }
          .continuity-actions button {
            width: 100%;
            min-height: 34px;
            padding: 5px 7px !important;
          }
          .continuity-details,
          .continuity-extra {
            display: none !important;
          }
          .continuity-details.expanded,
          .continuity-extra.expanded {
            display: grid !important;
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </section>
  );
}

const buttonStyle: React.CSSProperties = {
  border: '1px solid #d8d3cb',
  background: '#fff',
  borderRadius: 8,
  padding: '6px 9px',
  fontSize: 12,
  fontWeight: 800,
  color: 'var(--text)',
  cursor: 'pointer',
};
