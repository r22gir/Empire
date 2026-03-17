'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Terminal, Server, GitBranch, RefreshCw, Loader2,
  Play, Activity, CheckCircle2, XCircle, Clock,
} from 'lucide-react';
import { API } from '../../lib/api';

interface ServiceInfo {
  name: string;
  port: number;
  running: boolean;
  pid: number | null;
}

interface GitInfo {
  branch: string;
  last_commit_hash: string;
  message: string;
  uncommitted_count: number;
}

interface AuditEntry {
  id: number;
  timestamp: string;
  tool: string;
  params: string | null;
  result: string | null;
  desk: string | null;
  success: number;
  duration_ms: number;
}

interface HealthResult {
  services: ServiceInfo[];
  endpoints: { label: string; path: string; ok: boolean; status?: number }[];
  passed: number;
  failed: number;
}

export default function DevPanel() {
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [git, setGit] = useState<GitInfo | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [terminalOutput, setTerminalOutput] = useState<string[]>(['[Atlas] CodeForge Dev Panel initialized.']);
  const [loading, setLoading] = useState(true);
  const [healthRunning, setHealthRunning] = useState(false);
  const termRef = useRef<HTMLDivElement>(null);

  const addTermLine = useCallback((line: string, type: 'success' | 'error' | 'info' | 'warning' = 'info') => {
    const ts = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const prefix = type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : '→';
    setTerminalOutput(prev => [...prev.slice(-100), `${ts} ${prefix} ${line}`]);
  }, []);

  const fetchAll = useCallback(async () => {
    try {
      const [statusRes, gitRes, auditRes] = await Promise.all([
        fetch(`${API}/dev/status`).then(r => r.json()).catch(() => ({ services: [] })),
        fetch(`${API}/dev/git`).then(r => r.json()).catch(() => null),
        fetch(`${API}/dev/audit?limit=20`).then(r => r.json()).catch(() => ({ executions: [] })),
      ]);
      setServices(statusRes.services || []);
      setGit(gitRes);
      setAudit(auditRes.executions || []);
    } catch {
      addTermLine('Failed to fetch dev data', 'error');
    }
    setLoading(false);
  }, [addTermLine]);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  useEffect(() => {
    if (termRef.current) {
      termRef.current.scrollTop = termRef.current.scrollHeight;
    }
  }, [terminalOutput]);

  const runHealthCheck = async () => {
    setHealthRunning(true);
    addTermLine('Running full health check...', 'info');
    try {
      const res = await fetch(`${API}/dev/health`);
      const data: HealthResult = await res.json();

      data.services.forEach(s => {
        addTermLine(
          `Service ${s.name} (:${s.port}): ${s.running ? 'UP' : 'DOWN'}`,
          s.running ? 'success' : 'error'
        );
      });
      data.endpoints.forEach(e => {
        addTermLine(
          `${e.label} ${e.path}: ${e.ok ? e.status || 'OK' : 'FAIL'}`,
          e.ok ? 'success' : 'error'
        );
      });
      addTermLine(`Health: ${data.passed} passed, ${data.failed} failed`, data.failed > 0 ? 'warning' : 'success');

      setServices(data.services);
    } catch {
      addTermLine('Health check failed', 'error');
    }
    setHealthRunning(false);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin" size={20} style={{ color: '#b8960c' }} />
      </div>
    );
  }

  const runningCount = services.filter(s => s.running).length;

  return (
    <div style={{ padding: '20px 24px', maxWidth: 1200, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Terminal size={22} style={{ color: '#b8960c' }} />
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>
          CodeForge — Dev Panel
        </h2>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button
            onClick={runHealthCheck}
            disabled={healthRunning}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 10, border: 'none',
              background: '#b8960c', color: '#fff', fontSize: 12,
              fontWeight: 700, cursor: 'pointer', minHeight: 44,
              opacity: healthRunning ? 0.6 : 1,
            }}
          >
            {healthRunning ? <Loader2 size={14} className="animate-spin" /> : <Activity size={14} />}
            Run Health Check
          </button>
          <button
            onClick={fetchAll}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 14px', borderRadius: 10,
              border: '1px solid #ece8e0', background: '#faf9f7',
              fontSize: 12, cursor: 'pointer', minHeight: 44,
              color: '#666',
            }}
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16 }}>
        {/* Terminal Output */}
        <div style={{
          background: '#1e1e1e', borderRadius: 14, overflow: 'hidden',
          border: '1px solid #333',
        }}>
          <div style={{
            padding: '8px 14px', background: '#2d2d2d',
            borderBottom: '1px solid #444', fontSize: 11,
            color: '#888', fontFamily: 'JetBrains Mono, monospace',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <Terminal size={12} /> Terminal Output
          </div>
          <div
            ref={termRef}
            style={{
              padding: '12px 14px', height: 320, overflowY: 'auto',
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
              lineHeight: 1.6, color: '#d4d4d4',
            }}
          >
            {terminalOutput.map((line, i) => (
              <div key={i} style={{
                color: line.includes('✅') ? '#4ec9b0' :
                       line.includes('❌') ? '#f44747' :
                       line.includes('⚠️') ? '#b8960c' : '#d4d4d4',
              }}>
                {line}
              </div>
            ))}
          </div>
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Services */}
          <div style={{
            background: '#faf9f7', border: '1px solid #ece8e0',
            borderRadius: 14, padding: '14px 16px',
          }}>
            <div style={{
              fontSize: 11, color: '#999', textTransform: 'uppercase',
              letterSpacing: 0.5, marginBottom: 10, display: 'flex',
              alignItems: 'center', gap: 6,
            }}>
              <Server size={12} /> Services ({runningCount}/{services.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {services.map(s => (
                <div key={s.name} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '6px 10px', background: '#f5f2ed',
                  borderRadius: 8, fontSize: 12,
                }}>
                  {s.running ?
                    <CheckCircle2 size={14} style={{ color: '#16a34a', flexShrink: 0 }} /> :
                    <XCircle size={14} style={{ color: '#dc2626', flexShrink: 0 }} />
                  }
                  <span style={{ flex: 1, fontWeight: 600, color: '#444' }}>{s.name}</span>
                  <span style={{ color: '#999', fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
                    :{s.port}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Git */}
          {git && (
            <div style={{
              background: '#faf9f7', border: '1px solid #ece8e0',
              borderRadius: 14, padding: '14px 16px',
            }}>
              <div style={{
                fontSize: 11, color: '#999', textTransform: 'uppercase',
                letterSpacing: 0.5, marginBottom: 10, display: 'flex',
                alignItems: 'center', gap: 6,
              }}>
                <GitBranch size={12} /> Git
              </div>
              <div style={{ fontSize: 12, color: '#555', display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div>
                  <span style={{ color: '#999' }}>Branch:</span>{' '}
                  <span style={{ fontWeight: 600 }}>{git.branch}</span>
                </div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
                  <span style={{ color: '#b8960c' }}>{git.last_commit_hash}</span>{' '}
                  {git.message?.slice(0, 50)}
                </div>
                <div>
                  <span style={{ color: '#999' }}>Uncommitted:</span>{' '}
                  <span style={{
                    fontWeight: 600,
                    color: git.uncommitted_count > 0 ? '#d97706' : '#16a34a',
                  }}>
                    {git.uncommitted_count === 0 ? 'Clean' : git.uncommitted_count}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recent Tool Executions */}
      <div style={{
        background: '#faf9f7', border: '1px solid #ece8e0',
        borderRadius: 14, padding: '14px 16px',
      }}>
        <div style={{
          fontSize: 11, color: '#999', textTransform: 'uppercase',
          letterSpacing: 0.5, marginBottom: 10, display: 'flex',
          alignItems: 'center', gap: 6,
        }}>
          <Clock size={12} /> Recent Tool Executions
        </div>
        {audit.length === 0 ? (
          <div style={{ fontSize: 12, color: '#bbb', padding: '8px 0' }}>
            No tool executions recorded yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {audit.slice(0, 15).map(entry => {
              const ts = entry.timestamp ? new Date(entry.timestamp + 'Z').toLocaleTimeString('en-US', {
                hour12: false, hour: '2-digit', minute: '2-digit',
              }) : '--:--';
              return (
                <div key={entry.id} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '5px 10px', background: '#f5f2ed',
                  borderRadius: 6, fontSize: 12,
                }}>
                  {entry.success ?
                    <CheckCircle2 size={12} style={{ color: '#16a34a', flexShrink: 0 }} /> :
                    <XCircle size={12} style={{ color: '#dc2626', flexShrink: 0 }} />
                  }
                  <span style={{ color: '#999', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, width: 40 }}>
                    {ts}
                  </span>
                  <span style={{ color: '#888', fontSize: 10 }}>{entry.desk || 'max'}</span>
                  <span style={{ fontWeight: 600, color: '#444' }}>{entry.tool}</span>
                  {entry.duration_ms > 0 && (
                    <span style={{ marginLeft: 'auto', color: '#bbb', fontSize: 10 }}>
                      {entry.duration_ms}ms
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
