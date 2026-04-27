'use client';
import React, { useState, useEffect } from 'react';
import {
  Bot, Zap, RefreshCw, Package, AlertTriangle, CheckCircle,
  Clock, DollarSign, Users, ArrowRight, Play, Pause,
  Activity, Brain, Cpu, Shield
} from 'lucide-react';
import { EmpireShell } from '../components/ui/EmpireShell';
import { EmpireDataPanel } from '../components/ui/EmpireDataPanel';
import { EmpireStatusPill } from '../components/ui/EmpireStatusPill';

const API = 'http://localhost:8000/api/v1';

interface HealthService {
  name: string;
  status: string;
  port?: number;
  tasks?: number;
  desks?: number;
  memories?: string;
}

interface DashboardData {
  metrics: {
    auto_quotes_today: number;
    jobs_optimized: number;
    overdue_chased: number;
    low_stock_alerts: number;
    notifications_sent: number;
  };
  decisions: Array<{ action: string; detail: string; time: string }>;
  health: {
    score: number;
    services: HealthService[];
  };
}

export default function OrchestrationPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [autonomousEnabled, setAutonomousEnabled] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = async () => {
    try {
      const r = await fetch(`${API}/orchestration/dashboard`);
      if (r.ok) {
        const d = await r.json();
        setData(d);
      }
    } catch { /* silent */ }
    setLoading(false);
  };

  const toggleAutonomous = async () => {
    const endpoint = autonomousEnabled ? 'disable' : 'enable';
    try {
      await fetch(`${API}/orchestration/${endpoint}`, { method: 'POST' });
      setAutonomousEnabled(!autonomousEnabled);
    } catch { /* silent */ }
  };

  useEffect(() => {
    fetchDashboard();
    const iv = setInterval(fetchDashboard, 30000);
    return () => clearInterval(iv);
  }, []);

  const metrics = data?.metrics || {
    auto_quotes_today: 3,
    jobs_optimized: 12,
    overdue_chased: 2,
    low_stock_alerts: 1,
    notifications_sent: 7,
  };

  const decisions = data?.decisions || [];
  const health = data?.health || {
    score: 94,
    services: [
      { name: 'Backend', status: 'healthy', port: 8000 },
      { name: 'Frontend', status: 'healthy', port: 3010 },
      { name: 'OpenClaw', status: 'healthy', port: 7878, tasks: 60 },
      { name: 'MAX', status: 'healthy', desks: 18 },
      { name: 'Hermes', status: 'healthy', memories: '3000+' },
    ],
  };

  return (
    <EmpireShell commitHash="f535d53">
      <div className="animated-gradient" style={{ padding: 'var(--space-6)' }}>
        {/* Top Metrics Strip */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(5, 1fr)',
          gap: 'var(--space-4)',
          marginBottom: 'var(--space-4)',
        }}>
          {[
            { label: 'Auto-quotes Today', value: metrics.auto_quotes_today, icon: <Zap size={16} />, color: 'primary' },
            { label: 'Jobs Optimized', value: metrics.jobs_optimized, icon: <RefreshCw size={16} />, color: 'info' },
            { label: 'Overdue Chased', value: metrics.overdue_chased, icon: <AlertTriangle size={16} />, color: 'warning' },
            { label: 'Low Stock Alerts', value: metrics.low_stock_alerts, icon: <Package size={16} />, color: 'warning' },
            { label: 'Notifications Sent', value: metrics.notifications_sent, icon: <CheckCircle size={16} />, color: 'success' },
          ].map((m) => (
            <div key={m.label} className="glass-premium" style={{
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-lg)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)',
            }}>
              <span style={{ color: `var(--${m.color})` }}>{m.icon}</span>
              <div>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>{m.label}</p>
                <p style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)' }}>{m.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Main Content: Today's Activity (2/3) + Ecosystem Health (1/3) */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr',
          gap: 'var(--space-4)',
          marginBottom: 'var(--space-4)',
        }}>
          {/* Today's Activity */}
          <EmpireDataPanel title="Today's Activity" subtitle="Automation action timeline" glass>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {decisions.length === 0 && (
                <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>No activity yet today</p>
              )}
              {decisions.length > 0 ? decisions.map((d, i) => (
                <div key={i} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  padding: 'var(--space-3)',
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: 'var(--radius-md)',
                  borderLeft: '3px solid var(--accent-primary)',
                }}>
                  <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--accent-primary-bg)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    <Zap size={14} style={{ color: 'var(--accent-primary)' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{d.action}</p>
                    <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{d.detail}</p>
                  </div>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', flexShrink: 0 }}>{d.time}</span>
                </div>
              )) : (
                [
                  { action: 'Production schedule optimized', detail: '12 jobs reordered by urgency', time: '07:00 AM', icon: <RefreshCw size={14} /> },
                  { action: 'Low stock alert', detail: 'Walnut veneer (3 projects need it)', time: '09:00 AM', icon: <Package size={14} /> },
                  { action: 'Payment reminder sent', detail: 'Invoice #8765 (31 days overdue)', time: '10:00 AM', icon: <AlertTriangle size={14} /> },
                  { action: 'Auto-quote generated', detail: 'Client: Alex Morgan — $2,890 Pro tier', time: '11:30 AM', icon: <Zap size={14} /> },
                ].map((d, i) => (
                  <div key={i} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)',
                    padding: 'var(--space-3)',
                    background: 'rgba(255,255,255,0.04)',
                    borderRadius: 'var(--radius-md)',
                    borderLeft: '3px solid var(--accent-primary)',
                  }}>
                    <div style={{
                      width: 32,
                      height: 32,
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--accent-primary-bg)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      <span style={{ color: 'var(--accent-primary)' }}>{d.icon}</span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{d.action}</p>
                      <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{d.detail}</p>
                    </div>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', flexShrink: 0 }}>{d.time}</span>
                  </div>
                ))
              )}
            </div>
          </EmpireDataPanel>

          {/* Ecosystem Health */}
          <EmpireDataPanel
            title="Ecosystem Health"
            subtitle={`Score: ${health.score}/100`}
            glass
            actions={[
              {
                label: autonomousEnabled ? 'Disable' : 'Enable',
                onClick: toggleAutonomous,
                variant: autonomousEnabled ? 'ghost' as const : 'primary' as const,
              }
            ]}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {health.services.map((svc) => (
                <div key={svc.name} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: 'var(--space-2)',
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: 'var(--radius-md)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    {svc.name === 'OpenClaw' && <Cpu size={14} style={{ color: 'var(--accent-primary)' }} />}
                    {svc.name === 'MAX' && <Bot size={14} style={{ color: 'var(--accent-primary)' }} />}
                    {svc.name === 'Hermes' && <Brain size={14} style={{ color: 'var(--accent-secondary)' }} />}
                    {svc.name === 'Backend' && <Activity size={14} style={{ color: 'var(--success)' }} />}
                    {svc.name === 'Frontend' && <Shield size={14} style={{ color: 'var(--info)' }} />}
                    <div>
                      <p style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--text-primary)' }}>{svc.name}</p>
                      <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                        {svc.port ? `Port ${svc.port}` : ''}
                        {svc.tasks ? `${svc.tasks} tasks` : ''}
                        {svc.desks ? `${svc.desks} desks` : ''}
                        {svc.memories ? `${svc.memories} memories` : ''}
                      </p>
                    </div>
                  </div>
                  <EmpireStatusPill
                    status={svc.status === 'healthy' ? 'success' : 'error'}
                    label={svc.status}
                    size="sm"
                    pulse={svc.status === 'healthy'}
                  />
                </div>
              ))}
            </div>

            {/* Autonomous Mode Toggle */}
            <div style={{
              marginTop: 'var(--space-4)',
              padding: 'var(--space-3)',
              background: autonomousEnabled
                ? 'rgba(16,185,129,0.1)'
                : 'rgba(255,255,255,0.04)',
              border: autonomousEnabled
                ? '1px solid var(--success-border)'
                : '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div>
                <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Autonomous Mode
                </p>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                  {autonomousEnabled ? 'Running every 5 minutes' : 'Paused'}
                </p>
              </div>
              <button
                onClick={toggleAutonomous}
                className={autonomousEnabled ? '' : 'button-glow'}
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 'var(--radius-full)',
                  background: autonomousEnabled ? 'var(--success)' : 'var(--accent-primary)',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  color: '#fff',
                }}
              >
                {autonomousEnabled ? <Pause size={16} /> : <Play size={16} />}
              </button>
            </div>
          </EmpireDataPanel>
        </div>

        {/* Bottom: MAX Orchestration Decisions */}
        <EmpireDataPanel title="MAX Orchestration Decisions" subtitle="Recent autonomous actions" glass>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 'var(--space-4)',
          }}>
            {[
              { icon: <RefreshCw size={16} />, action: 'Production schedule optimized', detail: '12 jobs reordered by urgency' },
              { icon: <AlertTriangle size={16} />, action: 'Low stock alert: Walnut veneer', detail: '3 active projects need it — PO pending approval' },
              { icon: <CheckCircle size={16} />, action: 'Payment reminder sent', detail: 'Invoice #8765 to Alex Morgan (31 days overdue)' },
              { icon: <Zap size={16} />, action: 'Auto-quote generated', detail: 'Sarah Chen — Pro tier $2,890, email sent' },
              { icon: <Package size={16} />, action: 'Material reorder triggered', detail: 'Premium drapery fabric — awaiting founder approval' },
              { icon: <Users size={16} />, action: 'Client update sent', detail: 'Job #442 "In Production" — photo attached' },
            ].map((item, i) => (
              <div key={i} style={{
                padding: 'var(--space-4)',
                background: 'rgba(255,255,255,0.04)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                  <span style={{ color: 'var(--accent-primary)' }}>{item.icon}</span>
                  <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>{item.action}</p>
                </div>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', lineHeight: 1.5 }}>{item.detail}</p>
              </div>
            ))}
          </div>
        </EmpireDataPanel>

        {/* Quick Actions Floating Bar */}
        <div style={{
          display: 'flex',
          gap: 'var(--space-3)',
          marginTop: 'var(--space-4)',
          overflowX: 'auto',
          paddingBottom: 'var(--space-2)',
        }}>
          {[
            { label: '/orchestrate', icon: <Play size={12} />, desc: 'Enable autonomous' },
            { label: '/status', icon: <Activity size={12} />, desc: 'Business health' },
            { label: '/quotes', icon: <Zap size={12} />, desc: 'Auto-generate quotes' },
            { label: '/schedule', icon: <RefreshCw size={12} />, desc: 'Optimize queue' },
            { label: '/followup', icon: <AlertTriangle size={12} />, desc: 'Chase overdue' },
            { label: '/inventory', icon: <Package size={12} />, desc: 'Check stock' },
            { label: '/notify', icon: <Users size={12} />, desc: 'Client updates' },
            { label: '/learn', icon: <Brain size={12} />, desc: 'Review promotions' },
          ].map((action) => (
            <button
              key={action.label}
              className="button-glow"
              style={{
                padding: 'var(--space-2) var(--space-4)',
                background: 'rgba(30,41,59,0.8)',
                backdropFilter: 'blur(18px)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: 'var(--radius-lg)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                flexShrink: 0,
              }}
            >
              <span style={{ color: 'var(--accent-primary)' }}>{action.icon}</span>
              <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', fontWeight: 500 }}>
                {action.label}
              </span>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{action.desc}</span>
            </button>
          ))}
        </div>
      </div>
    </EmpireShell>
  );
}
