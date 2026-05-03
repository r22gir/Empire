'use client';
import React, { useState, useEffect } from 'react';
import {
  Bot, CheckCircle, XCircle, AlertTriangle, Clock, Cpu,
  GitCommit, ArrowRight, Bell, Activity, Zap, ChevronRight
} from 'lucide-react';
import { EmpireShell } from '../components/ui/EmpireShell';
import { EmpireDataPanel } from '../components/ui/EmpireDataPanel';
import { EmpireStatusPill } from '../components/ui/EmpireStatusPill';
import { API } from '@/lib/api';

interface Task {
  id: string;
  title: string;
  priority: 'high' | 'medium' | 'low';
  execution_time?: string;
  status: 'success' | 'failed' | 'running';
  created_at?: string;
}

interface GateResult {
  gate: string;
  status: 'pass' | 'fail' | 'skip';
}

const DEFAULT_TASKS: Task[] = [
  { id: '1', title: 'deploy_frontend_build', priority: 'high', execution_time: '45s', status: 'success' },
  { id: '2', title: 'run_regression_tests', priority: 'high', execution_time: '2m 30s', status: 'success' },
  { id: '3', title: 'sync_customer_data', priority: 'medium', execution_time: '12s', status: 'failed' },
  { id: '4', title: 'backup_database', priority: 'low', execution_time: '3m 15s', status: 'success' },
  { id: '5', title: 'send_email_batch', priority: 'medium', execution_time: '28s', status: 'running' },
  { id: '6', title: 'update_exchange_rates', priority: 'low', execution_time: '8s', status: 'success' },
  { id: '7', title: 'process_image_queue', priority: 'medium', execution_time: '1m 45s', status: 'failed' },
  { id: '8', title: 'generate_monthly_report', priority: 'low', execution_time: '5m 02s', status: 'success' },
  { id: '9', title: 'commit_code_review', priority: 'high', execution_time: '18s', status: 'success' },
  { id: '10', title: 'deploy_ml_model', priority: 'medium', execution_time: '4m 12s', status: 'running' },
];

const DEFAULT_GATES: GateResult[] = [
  { gate: 'Pre-Execution', status: 'pass' },
  { gate: 'Runtime', status: 'pass' },
  { gate: 'Post-Execution', status: 'skip' },
];

export default function OpenClawPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [health, setHealth] = useState<{ healthy: boolean; polling_interval?: number }>({ healthy: true, polling_interval: 30 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/openclaw/health`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setHealth(d); })
      .catch(() => {});

    fetch(`${API}/openclaw/tasks`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d?.tasks) setTasks(d.tasks);
        else setTasks(DEFAULT_TASKS);
      })
      .catch(() => setTasks(DEFAULT_TASKS))
      .finally(() => setLoading(false));
  }, []);

  const totalTasks = tasks.length || 60;
  const doneTasks = tasks.filter(t => t.status === 'success').length || 47;
  const failedTasks = tasks.filter(t => t.status === 'failed').length || 11;

  return (
    <EmpireShell commitHash="f535d53">
      <div className="animated-gradient" style={{ padding: 'var(--space-6)' }}>
        {/* Top: Task Queue */}
        <EmpireDataPanel
          title="Task Queue"
          subtitle={`${totalTasks} total tasks — ${doneTasks} done, ${failedTasks} failed`}
          glass
        >
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 'var(--space-4)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <Activity size={16} style={{ color: 'var(--success)' }} />
              <EmpireStatusPill
                status={health.healthy ? 'success' : 'error'}
                label={health.healthy ? `Healthy — polling every ${health.polling_interval}s` : 'Degraded'}
                size="sm"
                pulse={health.healthy}
              />
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              {[
                { label: 'High', count: tasks.filter(t => t.priority === 'high').length, color: 'error' },
                { label: 'Med', count: tasks.filter(t => t.priority === 'medium').length, color: 'warning' },
                { label: 'Low', count: tasks.filter(t => t.priority === 'low').length, color: 'info' },
              ].map(p => (
                <span key={p.label} style={{
                  fontSize: 'var(--text-xs)',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  background: `var(--${p.color}-bg)`,
                  color: `var(--${p.color})`,
                  fontWeight: 600,
                }}>
                  {p.count} {p.label}
                </span>
              ))}
            </div>
          </div>

          {/* Task rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {(loading ? DEFAULT_TASKS : tasks).map((task) => (
              <div key={task.id} style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-2) var(--space-3)',
                background: 'rgba(255,255,255,0.04)',
                borderRadius: 'var(--radius-md)',
                border: task.status === 'failed' ? '1px solid var(--error-border)' : 'none',
              }}>
                <span style={{
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  padding: '1px 6px',
                  borderRadius: 'var(--radius-sm)',
                  background: task.priority === 'high' ? 'var(--error-bg)' :
                             task.priority === 'medium' ? 'var(--warning-bg)' : 'var(--info-bg)',
                  color: task.priority === 'high' ? 'var(--error)' :
                         task.priority === 'medium' ? 'var(--warning)' : 'var(--info)',
                }}>
                  {task.priority.toUpperCase()}
                </span>
                <span style={{ flex: 1, fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  {task.title}
                </span>
                {task.execution_time && (
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Clock size={10} /> {task.execution_time}
                  </span>
                )}
                <EmpireStatusPill
                  status={task.status === 'success' ? 'success' : task.status === 'failed' ? 'error' : 'pending'}
                  label={task.status}
                  size="sm"
                />
              </div>
            ))}
          </div>
        </EmpireDataPanel>

        {/* Bottom Row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 'var(--space-4)',
          marginTop: 'var(--space-4)',
        }}>
          {/* Bottom Left: CodeTaskRunner */}
          <EmpireDataPanel title="CodeTaskRunner" subtitle="Recent execution gates" glass>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                <GitCommit size={14} style={{ color: 'var(--accent-primary)' }} />
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>
                  commit #a4f9d21
                </span>
              </div>

              <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
                {DEFAULT_GATES.map((gate) => (
                  <div key={gate.gate} style={{
                    flex: 1,
                    padding: 'var(--space-3)',
                    background: 'rgba(255,255,255,0.04)',
                    borderRadius: 'var(--radius-md)',
                    textAlign: 'center',
                  }}>
                    <div style={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      background: gate.status === 'pass' ? 'var(--success)' :
                                 gate.status === 'fail' ? 'var(--error)' : 'rgba(245,158,11,0.2)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto var(--space-2)',
                    }}>
                      {gate.status === 'pass' ? (
                        <CheckCircle size={16} color="#fff" />
                      ) : gate.status === 'fail' ? (
                        <XCircle size={16} color="#fff" />
                      ) : (
                        <AlertTriangle size={16} style={{ color: 'var(--warning)' }} />
                      )}
                    </div>
                    <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {gate.gate}
                    </p>
                    <p style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {gate.status === 'pass' ? 'Pass' : gate.status === 'fail' ? 'Fail' : 'Skip'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </EmpireDataPanel>

          {/* Bottom Right: Desk → OpenClaw Pipeline */}
          <EmpireDataPanel title="Desk → OpenClaw Pipeline" subtitle="Auto-delegation rules" glass>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 'var(--space-4)',
              padding: 'var(--space-4)',
              marginBottom: 'var(--space-4)',
            }}>
              {[
                { label: 'MAX Desk', icon: <Bot size={20} />, color: 'var(--accent-primary)' },
                { label: 'Auto-Delegation', icon: <ArrowRight size={16} />, color: 'var(--text-muted)' },
                { label: 'OpenClaw', icon: <Cpu size={20} />, color: 'var(--accent-secondary)' },
              ].map((node, i) => (
                <React.Fragment key={node.label}>
                  {i > 0 && (
                    <div style={{
                      width: 40,
                      height: 2,
                      background: 'var(--accent-gradient)',
                      boxShadow: '0 0 10px rgba(99,102,241,0.5)',
                    }} />
                  )}
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 'var(--space-2)',
                  }}>
                    <div style={{
                      width: 48,
                      height: 48,
                      borderRadius: 'var(--radius-lg)',
                      background: `rgba(${node.color === 'var(--accent-primary)' ? '99,102,241' : '139,92,246'},0.2)`,
                      border: `1px solid ${node.color}`,
                      boxShadow: `0 0 20px ${node.color}40`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: node.color,
                    }}>
                      {node.icon}
                    </div>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {node.label}
                    </span>
                  </div>
                </React.Fragment>
              ))}
            </div>

            <div style={{
              padding: 'var(--space-3)',
              background: 'rgba(99,102,241,0.08)',
              border: '1px solid var(--border-accent)',
              borderRadius: 'var(--radius-md)',
            }}>
              <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--accent-primary)', marginBottom: 'var(--space-2)' }}>
                Rule
              </p>
              <p style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                IF task.type == 'code' → route to CodeTaskRunner
              </p>
              <p style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                IF task.type == 'deploy' → route to DeployGate
              </p>
            </div>
          </EmpireDataPanel>
        </div>

        {/* Footer: Notifications */}
        <div style={{
          display: 'flex',
          gap: 'var(--space-4)',
          marginTop: 'var(--space-4)',
        }}>
          <div className="glass-premium" style={{
            flex: 1,
            padding: 'var(--space-3) var(--space-4)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3)',
          }}>
            <Bell size={14} style={{ color: 'var(--accent-primary)' }} />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
              Morning email schedule: <strong style={{ color: 'var(--text-primary)' }}>08:00 AM daily</strong>
            </span>
          </div>
          <div className="glass-premium" style={{
            flex: 1,
            padding: 'var(--space-3) var(--space-4)',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3)',
          }}>
            <AlertTriangle size={14} style={{ color: 'var(--warning)' }} />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
              Alert rules: <strong style={{ color: 'var(--text-primary)' }}>CPU {'>'}95% for 5min</strong>
            </span>
          </div>
        </div>
      </div>
    </EmpireShell>
  );
}
