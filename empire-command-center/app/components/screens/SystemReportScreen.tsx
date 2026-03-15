'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../lib/api';
import {
  RefreshCw, CheckCircle2, XCircle, AlertTriangle, Cpu, HardDrive, Database,
  GitCommit, Sparkles, ArrowRight, Plug, Unplug, Clock, Bug, Lightbulb,
  Activity, ChevronDown, ChevronRight, Monitor
} from 'lucide-react';

interface SystemReport {
  generated_at: string;
  system: any;
  modules: any[];
  recent_changes: any[];
  recent_diff_summary?: string;
  desk_reports: any[];
  connectivity: any[];
  suggestions: string[];
  bugs: any[];
}

export default function SystemReportScreen() {
  const [report, setReport] = useState<SystemReport | null>(null);
  const [changelog, setChangelog] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    system: true, modules: true, connectivity: true, changes: false, desks: false, bugs: true, suggestions: true,
  });

  const fetchReport = useCallback(async () => {
    try {
      const [reportRes, changelogRes] = await Promise.all([
        fetch(`${API}/max/system-report`),
        fetch(`${API}/max/changelog`),
      ]);
      if (reportRes.ok) setReport(await reportRes.json());
      if (changelogRes.ok) setChangelog(await changelogRes.json());
    } catch (e) {
      console.error('Failed to fetch system report:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchReport, 60000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchReport]);

  const toggle = (key: string) => setExpandedSections(s => ({ ...s, [key]: !s[key] }));

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw size={32} style={{ color: 'var(--gold)' }} className="mx-auto mb-3 animate-spin" />
          <p style={{ fontSize: 14, color: 'var(--muted)' }}>Generating system report...</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <XCircle size={32} style={{ color: 'var(--red)' }} className="mx-auto mb-3" />
          <p style={{ fontSize: 14, color: 'var(--muted)' }}>Failed to load report. Is the backend running?</p>
          <button onClick={fetchReport}
            className="filter-tab active" style={{ marginTop: 12 }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  const connectedModules = report.modules.filter(m => m.frontend === true).length;
  const disconnectedModules = report.modules.filter(m => m.frontend === false).length;
  const onlineServices = report.connectivity.filter(c => c.status === 'online').length;

  return (
    <div className="flex-1 overflow-y-auto" style={{ padding: '28px 36px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="flex items-center gap-2" style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)' }}>
            <Monitor size={22} style={{ color: 'var(--gold)' }} />
            MAX System Report
          </h1>
          <p style={{ fontSize: 13, color: 'var(--muted)', marginTop: 4 }} suppressHydrationWarning>
            Generated {new Date(report.generated_at).toLocaleString()}
            {autoRefresh && <span style={{ marginLeft: 8, color: 'var(--green)' }}>● Auto-refresh every 60s</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setAutoRefresh(!autoRefresh)}
            className="filter-tab"
            style={autoRefresh ? { background: 'var(--green-bg)', color: '#16a34a', borderColor: '#bbf7d0' } : {}}>
            {autoRefresh ? '● Live' : '○ Paused'}
          </button>
          <button onClick={() => { setLoading(true); fetchReport(); }}
            className="filter-tab active"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </div>

      {/* Quick Stats Bar */}
      <div className="section-label" style={{ marginBottom: 10 }}>System Overview</div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <StatCard icon={<Cpu size={18} />} label="CPU" value={`${report.system.cpu_percent || 0}%`}
          subtitle={`${report.system.cpu_cores || 20} cores`}
          color={report.system.cpu_percent > 80 ? 'var(--red)' : 'var(--green)'} />
        <StatCard icon={<HardDrive size={18} />} label="RAM" value={`${report.system.memory_percent || 0}%`}
          subtitle={`${report.system.memory_total_gb || 31} GB total`}
          color={report.system.memory_percent > 80 ? 'var(--red)' : 'var(--blue)'} />
        <StatCard icon={<Database size={18} />} label="Disk" value={`${report.system.disk_percent || 0}%`}
          subtitle={`${report.system.disk_total_gb || 0} GB total`}
          color={report.system.disk_percent > 80 ? 'var(--red)' : 'var(--purple)'} />
        <StatCard icon={<Plug size={18} />} label="Connected" value={`${connectedModules}/${report.modules.length}`}
          color="var(--green)" />
        <StatCard icon={<Clock size={18} />} label="Uptime" value={report.system.uptime || '--'}
          color="var(--gold)" />
      </div>

      {/* Connectivity */}
      <Section title="Service Connectivity" icon={<Activity size={18} />} sectionKey="connectivity"
        expanded={expandedSections.connectivity} onToggle={() => toggle('connectivity')}
        badge={`${onlineServices}/${report.connectivity.length} online`} badgeColor="#16a34a">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {report.connectivity.map(c => (
            <div key={c.service} className="empire-card flat" style={{
              background: c.status === 'online' ? 'var(--green-bg)' : 'var(--red-bg)',
              borderColor: c.status === 'online' ? '#bbf7d0' : '#fecaca',
            }}>
              <div className="flex items-center gap-2">
                {c.status === 'online' ? <CheckCircle2 size={14} style={{ color: 'var(--green)' }} /> : <XCircle size={14} style={{ color: 'var(--red)' }} />}
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{c.service}</span>
              </div>
              <p style={{ fontSize: 10, color: 'var(--muted)', marginTop: 4, fontFamily: 'monospace' }}>{c.url}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Modules */}
      <Section title="Module Inventory" icon={<Plug size={18} />} sectionKey="modules"
        expanded={expandedSections.modules} onToggle={() => toggle('modules')}
        badge={`${disconnectedModules} not wired`} badgeColor="#d97706">
        <div className="space-y-1">
          {report.modules.map(m => (
            <div key={m.name} className="flex items-center gap-3 px-4 py-2.5 rounded-[var(--radius-sm)] hover:bg-[var(--hover)] transition-colors">
              <div className="w-2 h-2 rounded-full shrink-0" style={{
                background: m.frontend === true ? 'var(--green)' : m.frontend === 'partial' ? '#d97706' : 'var(--border)',
              }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', width: 160 }} className="truncate">{m.name}</span>
              <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--muted)' }} className="flex-1">{m.endpoint}</span>
              <span className="status-pill" style={{
                ...(m.frontend === true
                  ? { background: 'var(--green-bg)', color: '#16a34a' }
                  : m.frontend === 'partial'
                    ? { background: 'var(--orange-bg)', color: '#d97706' }
                    : { background: '#f5f5f5', color: 'var(--muted)' }),
                fontSize: 10, padding: '3px 10px', borderRadius: 20,
              }}>
                {m.frontend === true ? 'Connected' : m.frontend === 'partial' ? 'Partial' : 'Backend Only'}
              </span>
            </div>
          ))}
        </div>
      </Section>

      {/* AI Desks */}
      <Section title="AI Desk Status" icon={<Sparkles size={18} />} sectionKey="desks"
        expanded={expandedSections.desks} onToggle={() => toggle('desks')}
        badge={`${report.desk_reports.length} desks`} badgeColor="#7c3aed">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {report.desk_reports.map(d => (
            <div key={d.id} className="empire-card flat">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full" style={{ background: 'var(--green)' }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{d.name}</span>
                <span style={{ fontSize: 10, color: 'var(--muted)', marginLeft: 'auto' }}>{d.status}</span>
              </div>
              <p style={{ fontSize: 10, color: 'var(--purple)', fontStyle: 'italic', marginBottom: 8 }}>{d.persona}</p>
              {d.domains && d.domains.length > 0 && (
                <div className="flex gap-1 flex-wrap mb-2">
                  {d.domains.slice(0, 4).map((dm: string) => (
                    <span key={dm} style={{ fontSize: 9, background: 'var(--hover)', color: 'var(--dim)', padding: '2px 8px', borderRadius: 6 }}>{dm}</span>
                  ))}
                </div>
              )}
              <div style={{ fontSize: 10, color: 'var(--muted)' }}>
                Can: {d.can_report?.slice(0, 2).join(', ')}
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Recent Changes */}
      <Section title="Recent Changes" icon={<GitCommit size={18} />} sectionKey="changes"
        expanded={expandedSections.changes} onToggle={() => toggle('changes')}
        badge={report.recent_diff_summary || `${report.recent_changes.length} commits`} badgeColor="#2563eb">
        <div className="space-y-1">
          {report.recent_changes.slice(0, 15).map((c, i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-2 rounded-[var(--radius-sm)] hover:bg-[var(--hover)] transition-colors">
              <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--gold)', width: 60 }} className="shrink-0">{c.hash}</span>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }} className="truncate">{c.message}</span>
            </div>
          ))}
        </div>
        {changelog?.new_features && changelog.new_features.length > 0 && (
          <div className="empire-card flat" style={{ marginTop: 14, background: 'var(--purple-bg)', borderColor: '#c4b5fd' }}>
            <p className="section-label" style={{ color: 'var(--purple)', marginBottom: 8 }}>New Features Detected</p>
            {changelog.new_features.slice(0, 5).map((f: any, i: number) => (
              <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
                <span style={{ fontSize: 10, color: 'var(--muted)', fontFamily: 'monospace' }}>{f.date?.split(' ')[0]}</span> — {f.description}
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Bugs */}
      <Section title="Known Issues" icon={<Bug size={18} />} sectionKey="bugs"
        expanded={expandedSections.bugs} onToggle={() => toggle('bugs')}
        badge={`${report.bugs.length} issues`} badgeColor={report.bugs.some(b => b.severity === 'high') ? '#dc2626' : '#d97706'}>
        <div className="space-y-2">
          {report.bugs.map((b, i) => (
            <div key={i} className="empire-card flat" style={{
              display: 'flex', alignItems: 'flex-start', gap: 8,
              background: b.severity === 'high' ? 'var(--red-bg)' : b.severity === 'medium' ? 'var(--orange-bg)' : '#f5f5f5',
              borderColor: b.severity === 'high' ? '#fecaca' : b.severity === 'medium' ? '#fde68a' : '#e5e5e5',
            }}>
              <AlertTriangle size={14} className="mt-0.5 shrink-0" style={{
                color: b.severity === 'high' ? 'var(--red)' : b.severity === 'medium' ? '#d97706' : 'var(--muted)',
              }} />
              <div>
                <span style={{
                  fontSize: 10, fontWeight: 700, textTransform: 'uppercase' as const, marginRight: 8,
                  color: b.severity === 'high' ? 'var(--red)' : b.severity === 'medium' ? '#d97706' : 'var(--muted)',
                }}>{b.severity}</span>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{b.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Suggestions */}
      <Section title="MAX Suggestions" icon={<Lightbulb size={18} />} sectionKey="suggestions"
        expanded={expandedSections.suggestions} onToggle={() => toggle('suggestions')}
        badge={`${report.suggestions.length} ideas`} badgeColor="#16a34a">
        <div className="space-y-2">
          {report.suggestions.map((s, i) => (
            <div key={i} className="empire-card flat" style={{
              display: 'flex', alignItems: 'flex-start', gap: 8,
              background: 'var(--green-bg)', borderColor: '#bbf7d0',
            }}>
              <ArrowRight size={14} style={{ color: 'var(--green)' }} className="mt-0.5 shrink-0" />
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{s}</span>
            </div>
          ))}
        </div>
      </Section>

      <div className="text-center py-6">
        <p style={{ fontSize: 10, color: 'var(--faint)' }}>MAX System Report v1.0 — Updates every 60 seconds when Live mode is enabled</p>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color, subtitle }: { icon: React.ReactNode; label: string; value: string; color: string; subtitle?: string }) {
  return (
    <div className="empire-card flat" style={{ padding: '12px 16px' }}>
      <div className="flex items-center gap-2 mb-1">
        <span style={{ color }}>{icon}</span>
        <span className="section-label" style={{ letterSpacing: 1 }}>{label}</span>
      </div>
      <span style={{ fontSize: 20, fontWeight: 700, fontFamily: 'monospace', color }}>{value}</span>
      {subtitle && <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>{subtitle}</div>}
    </div>
  );
}

function Section({ title, icon, sectionKey, expanded, onToggle, badge, badgeColor, children }: {
  title: string; icon: React.ReactNode; sectionKey: string;
  expanded: boolean; onToggle: () => void;
  badge?: string; badgeColor?: string; children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      <button onClick={onToggle}
        className="empire-card"
        style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px' }}>
        <span style={{ color: 'var(--gold)' }}>{icon}</span>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', flex: 1, textAlign: 'left' }}>{title}</span>
        {badge && (
          <span className="status-pill" style={{ color: badgeColor, background: badgeColor + '15', fontSize: 10, padding: '3px 10px', borderRadius: 20 }}>
            {badge}
          </span>
        )}
        {expanded ? <ChevronDown size={14} style={{ color: 'var(--muted)' }} /> : <ChevronRight size={14} style={{ color: 'var(--muted)' }} />}
      </button>
      {expanded && <div style={{ marginTop: 8, paddingLeft: 4 }}>{children}</div>}
    </div>
  );
}
