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
          <RefreshCw size={32} className="text-[#b8960c] mx-auto mb-3 animate-spin" />
          <p className="text-sm text-[#888]">Generating system report...</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <XCircle size={32} className="text-red-400 mx-auto mb-3" />
          <p className="text-sm text-[#888]">Failed to load report. Is the backend running?</p>
          <button onClick={fetchReport} className="mt-3 px-4 py-2 bg-[#b8960c] text-white rounded-lg text-sm font-bold">
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
    <div className="flex-1 overflow-y-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#1a1a1a] flex items-center gap-2">
            <Monitor size={24} className="text-[#b8960c]" />
            MAX System Report
          </h1>
          <p className="text-xs text-[#999] mt-1" suppressHydrationWarning>
            Generated {new Date(report.generated_at).toLocaleString()}
            {autoRefresh && <span className="ml-2 text-[#16a34a]">● Auto-refresh every 60s</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-2 rounded-lg text-xs font-bold border transition-all ${
              autoRefresh ? 'bg-[#f0fdf4] border-[#bbf7d0] text-[#16a34a]' : 'bg-white border-[#ddd] text-[#999]'
            }`}>
            {autoRefresh ? '● Live' : '○ Paused'}
          </button>
          <button onClick={() => { setLoading(true); fetchReport(); }}
            className="px-3 py-2 rounded-lg bg-[#b8960c] text-white text-xs font-bold flex items-center gap-1.5 hover:bg-[#a08509]">
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </div>

      {/* Quick Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <StatCard icon={<Cpu size={18} />} label="CPU" value={`${report.system.cpu_percent || 0}%`}
          color={report.system.cpu_percent > 80 ? '#dc2626' : '#16a34a'} />
        <StatCard icon={<HardDrive size={18} />} label="RAM" value={`${report.system.memory_percent || 0}%`}
          color={report.system.memory_percent > 80 ? '#dc2626' : '#2563eb'} />
        <StatCard icon={<Database size={18} />} label="Disk" value={`${report.system.disk_percent || 0}%`}
          color={report.system.disk_percent > 80 ? '#dc2626' : '#7c3aed'} />
        <StatCard icon={<Plug size={18} />} label="Connected" value={`${connectedModules}/${report.modules.length}`}
          color="#16a34a" />
        <StatCard icon={<Clock size={18} />} label="Uptime" value={report.system.uptime || '--'}
          color="#b8960c" />
      </div>

      {/* ── Connectivity ── */}
      <Section title="Service Connectivity" icon={<Activity size={18} />} sectionKey="connectivity"
        expanded={expandedSections.connectivity} onToggle={() => toggle('connectivity')}
        badge={`${onlineServices}/${report.connectivity.length} online`} badgeColor="#16a34a">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {report.connectivity.map(c => (
            <div key={c.service} className={`p-3 rounded-xl border ${c.status === 'online' ? 'bg-[#f0fdf4] border-[#bbf7d0]' : 'bg-red-50 border-red-200'}`}>
              <div className="flex items-center gap-2">
                {c.status === 'online' ? <CheckCircle2 size={14} className="text-[#16a34a]" /> : <XCircle size={14} className="text-red-500" />}
                <span className="text-sm font-bold text-[#1a1a1a]">{c.service}</span>
              </div>
              <p className="text-[10px] text-[#999] mt-1 font-mono">{c.url}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ── Modules ── */}
      <Section title="Module Inventory" icon={<Plug size={18} />} sectionKey="modules"
        expanded={expandedSections.modules} onToggle={() => toggle('modules')}
        badge={`${disconnectedModules} not wired`} badgeColor="#d97706">
        <div className="space-y-1">
          {report.modules.map(m => (
            <div key={m.name} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f5f3ef]">
              <div className={`w-2 h-2 rounded-full shrink-0 ${
                m.frontend === true ? 'bg-[#16a34a]' : m.frontend === 'partial' ? 'bg-[#d97706]' : 'bg-[#ddd]'
              }`} />
              <span className="text-sm font-semibold text-[#1a1a1a] w-40 truncate">{m.name}</span>
              <span className="text-[10px] font-mono text-[#999] flex-1">{m.endpoint}</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                m.frontend === true
                  ? 'bg-[#f0fdf4] text-[#16a34a]'
                  : m.frontend === 'partial'
                    ? 'bg-[#fffbeb] text-[#d97706]'
                    : 'bg-[#f5f5f5] text-[#999]'
              }`}>
                {m.frontend === true ? 'Connected' : m.frontend === 'partial' ? 'Partial' : 'Backend Only'}
              </span>
            </div>
          ))}
        </div>
      </Section>

      {/* ── AI Desks ── */}
      <Section title="AI Desk Status" icon={<Sparkles size={18} />} sectionKey="desks"
        expanded={expandedSections.desks} onToggle={() => toggle('desks')}
        badge={`${report.desk_reports.length} desks`} badgeColor="#7c3aed">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {report.desk_reports.map(d => (
            <div key={d.id} className="p-3 rounded-xl border border-[#ece8e1] bg-white">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-[#16a34a]" />
                <span className="text-sm font-bold text-[#1a1a1a]">{d.name}</span>
                <span className="text-[10px] text-[#999] ml-auto">{d.status}</span>
              </div>
              <p className="text-[10px] text-[#7c3aed] italic mb-2">{d.persona}</p>
              {d.domains && d.domains.length > 0 && (
                <div className="flex gap-1 flex-wrap mb-2">
                  {d.domains.slice(0, 4).map((dm: string) => (
                    <span key={dm} className="text-[9px] bg-[#f5f3ef] text-[#777] px-1.5 py-0.5 rounded">{dm}</span>
                  ))}
                </div>
              )}
              <div className="text-[10px] text-[#999]">
                Can: {d.can_report?.slice(0, 2).join(', ')}
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── Recent Changes ── */}
      <Section title="Recent Changes" icon={<GitCommit size={18} />} sectionKey="changes"
        expanded={expandedSections.changes} onToggle={() => toggle('changes')}
        badge={report.recent_diff_summary || `${report.recent_changes.length} commits`} badgeColor="#2563eb">
        <div className="space-y-1">
          {report.recent_changes.slice(0, 15).map((c, i) => (
            <div key={i} className="flex items-center gap-3 px-3 py-1.5 rounded-lg hover:bg-[#f5f3ef]">
              <span className="text-[10px] font-mono text-[#b8960c] w-16 shrink-0">{c.hash}</span>
              <span className="text-xs text-[#555] truncate">{c.message}</span>
            </div>
          ))}
        </div>
        {changelog?.new_features && changelog.new_features.length > 0 && (
          <div className="mt-4 p-3 rounded-xl bg-[#ede9fe] border border-[#c4b5fd]">
            <p className="text-[10px] font-bold text-[#7c3aed] mb-2">NEW FEATURES DETECTED</p>
            {changelog.new_features.slice(0, 5).map((f: any, i: number) => (
              <div key={i} className="text-xs text-[#555] mb-1">
                <span className="text-[10px] text-[#999] font-mono">{f.date?.split(' ')[0]}</span> — {f.description}
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* ── Bugs ── */}
      <Section title="Known Issues" icon={<Bug size={18} />} sectionKey="bugs"
        expanded={expandedSections.bugs} onToggle={() => toggle('bugs')}
        badge={`${report.bugs.length} issues`} badgeColor={report.bugs.some(b => b.severity === 'high') ? '#dc2626' : '#d97706'}>
        <div className="space-y-2">
          {report.bugs.map((b, i) => (
            <div key={i} className={`flex items-start gap-2 p-3 rounded-xl border ${
              b.severity === 'high' ? 'bg-red-50 border-red-200' :
              b.severity === 'medium' ? 'bg-[#fffbeb] border-[#fde68a]' :
              'bg-[#f5f5f5] border-[#e5e5e5]'
            }`}>
              <AlertTriangle size={14} className={`mt-0.5 shrink-0 ${
                b.severity === 'high' ? 'text-red-500' : b.severity === 'medium' ? 'text-[#d97706]' : 'text-[#999]'
              }`} />
              <div>
                <span className="text-[10px] font-bold uppercase mr-2" style={{
                  color: b.severity === 'high' ? '#dc2626' : b.severity === 'medium' ? '#d97706' : '#999'
                }}>{b.severity}</span>
                <span className="text-xs text-[#555]">{b.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── Suggestions ── */}
      <Section title="MAX Suggestions" icon={<Lightbulb size={18} />} sectionKey="suggestions"
        expanded={expandedSections.suggestions} onToggle={() => toggle('suggestions')}
        badge={`${report.suggestions.length} ideas`} badgeColor="#16a34a">
        <div className="space-y-2">
          {report.suggestions.map((s, i) => (
            <div key={i} className="flex items-start gap-2 p-3 rounded-xl bg-[#f0fdf4] border border-[#bbf7d0]">
              <ArrowRight size={14} className="text-[#16a34a] mt-0.5 shrink-0" />
              <span className="text-xs text-[#555]">{s}</span>
            </div>
          ))}
        </div>
      </Section>

      <div className="text-center py-6">
        <p className="text-[10px] text-[#ccc]">MAX System Report v1.0 — Updates every 60 seconds when Live mode is enabled</p>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  return (
    <div className="p-3 rounded-xl border border-[#ece8e1] bg-white">
      <div className="flex items-center gap-2 mb-1">
        <span style={{ color }}>{icon}</span>
        <span className="text-[10px] text-[#999] font-semibold">{label}</span>
      </div>
      <span className="text-lg font-bold font-mono" style={{ color }}>{value}</span>
    </div>
  );
}

function Section({ title, icon, sectionKey, expanded, onToggle, badge, badgeColor, children }: {
  title: string; icon: React.ReactNode; sectionKey: string;
  expanded: boolean; onToggle: () => void;
  badge?: string; badgeColor?: string; children: React.ReactNode;
}) {
  return (
    <div className="mb-4">
      <button onClick={onToggle}
        className="w-full flex items-center gap-2 p-3 rounded-xl bg-white border border-[#ece8e1] hover:border-[#b8960c] transition-all cursor-pointer">
        <span className="text-[#b8960c]">{icon}</span>
        <span className="text-sm font-bold text-[#1a1a1a] flex-1 text-left">{title}</span>
        {badge && <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ color: badgeColor, background: badgeColor + '15' }}>{badge}</span>}
        {expanded ? <ChevronDown size={14} className="text-[#999]" /> : <ChevronRight size={14} className="text-[#999]" />}
      </button>
      {expanded && <div className="mt-2 pl-1">{children}</div>}
    </div>
  );
}
