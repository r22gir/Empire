'use client';
import React, { useState, useEffect } from 'react';
import {
  Brain, Search, CheckCircle, AlertTriangle, Clock, Sparkles,
  Globe, ChevronRight, Shield, Zap
} from 'lucide-react';
import { EmpireShell } from '../components/ui/EmpireShell';
import { EmpireDataPanel } from '../components/ui/EmpireDataPanel';
import { EmpireStatusPill } from '../components/ui/EmpireStatusPill';
import { API } from '@/lib/api';

interface ValidationCard {
  id: string;
  name: string;
  status: 'pass' | 'fail' | 'pending';
}

interface BrowserSession {
  id: string;
  action: string;
  status: 'extracting' | 'validated' | 'auto_tagged' | 'blocked';
}

const DEFAULT_VALIDATIONS: ValidationCard[] = [
  { id: '1', name: 'Invoice Date Parsing', status: 'pass' },
  { id: '2', name: 'Vendor Name Extraction', status: 'pass' },
  { id: '3', name: 'Amount Normalization', status: 'pass' },
  { id: '4', name: 'Currency Detection', status: 'pending' },
  { id: '5', name: 'Tax Calculation', status: 'fail' },
];

const DEFAULT_SESSIONS: BrowserSession[] = [
  { id: '1', action: 'Extracting invoice data', status: 'validated' },
  { id: '2', action: 'Parsing vendor fields', status: 'auto_tagged' },
  { id: '3', action: 'Validating amount', status: 'extracting' },
  { id: '4', action: 'Blocking suspicious input', status: 'blocked' },
];

export default function HermesPage() {
  const [memoryCount, setMemoryCount] = useState(3000);
  const [validationCards, setValidationCards] = useState<ValidationCard[]>([]);
  const [browserSessions, setBrowserSessions] = useState<BrowserSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/hermes/memory`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d) {
          if (d.memory_count) setMemoryCount(d.memory_count);
          if (d.validations) setValidationCards(d.validations);
          if (d.sessions) setBrowserSessions(d.sessions);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const passCount = validationCards.filter(v => v.status === 'pass').length;
  const failCount = validationCards.filter(v => v.status === 'fail').length;
  const pendingCount = validationCards.filter(v => v.status === 'pending').length;

  return (
    <EmpireShell commitHash="f535d53">
      <div className="animated-gradient" style={{ padding: 'var(--space-6)' }}>
        {/* Top: Memory Bridge */}
        <EmpireDataPanel
          title="Memory Bridge"
          subtitle="Indexed memories for context injection"
          glass
        >
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-4)',
            marginBottom: 'var(--space-4)',
          }}>
            <div style={{ flex: 1 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-2) var(--space-3)',
              }}>
                <Search size={14} style={{ color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Search memories..."
                  style={{
                    flex: 1,
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-sm)',
                    outline: 'none',
                  }}
                />
              </div>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-2) var(--space-3)',
              background: 'var(--success-bg)',
              border: '1px solid var(--success-border)',
              borderRadius: 'var(--radius-md)',
              boxShadow: '0 0 20px rgba(16,185,129,0.2)',
            }}>
              <Zap size={14} style={{ color: 'var(--success)' }} />
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--success)' }}>
                Context Injection: 100% active
              </span>
            </div>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-3)',
            padding: 'var(--space-3)',
            background: 'rgba(139,92,246,0.1)',
            border: '1px solid var(--accent-secondary-border)',
            borderRadius: 'var(--radius-md)',
          }}>
            <Brain size={20} style={{ color: 'var(--accent-secondary)' }} />
            <div>
              <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>
                Indexed: {memoryCount.toLocaleString()}+ memories
              </p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                Context window fully populated · 99 summaries active
              </p>
            </div>
          </div>
        </EmpireDataPanel>

        {/* Middle Row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 'var(--space-4)',
          marginTop: 'var(--space-4)',
        }}>
          {/* Middle Left: Prep Intake */}
          <EmpireDataPanel title="Prep Intake" subtitle="Validation cards" glass>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {DEFAULT_VALIDATIONS.map((card) => (
                <div key={card.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  padding: 'var(--space-3)',
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: 'var(--radius-md)',
                  border: card.status === 'fail' ? '1px solid var(--error-border)' :
                             card.status === 'pass' ? '1px solid var(--success-border)' : 'none',
                }}>
                  {card.status === 'pass' ? (
                    <CheckCircle size={16} style={{ color: 'var(--success)' }} />
                  ) : card.status === 'fail' ? (
                    <AlertTriangle size={16} style={{ color: 'var(--error)' }} />
                  ) : (
                    <Clock size={16} style={{ color: 'var(--pending)' }} />
                  )}
                  <span style={{ flex: 1, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                    {card.name}
                  </span>
                  <EmpireStatusPill
                    status={card.status === 'pass' ? 'success' : card.status === 'fail' ? 'error' : 'pending'}
                    label={card.status}
                    size="sm"
                  />
                </div>
              ))}
            </div>

            <div style={{ marginTop: 'var(--space-4)' }}>
              <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>
                Flow
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                {['Form Load', 'Field Parse', 'Rule Validate', 'Commit'].map((step, i) => (
                  <React.Fragment key={step}>
                    {i > 0 && <ChevronRight size={12} style={{ color: 'var(--text-muted)' }} />}
                    <span style={{
                      fontSize: 'var(--text-xs)',
                      padding: '2px 8px',
                      background: 'rgba(99,102,241,0.1)',
                      border: '1px solid var(--border-accent)',
                      borderRadius: 'var(--radius-full)',
                      color: 'var(--accent-primary)',
                      fontWeight: 500,
                    }}>
                      {step}
                    </span>
                  </React.Fragment>
                ))}
              </div>
            </div>
          </EmpireDataPanel>

          {/* Middle Right: Browser Assist */}
          <EmpireDataPanel title="Browser Assist" subtitle="Active sessions" glass>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {DEFAULT_SESSIONS.map((session) => (
                <div key={session.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  padding: 'var(--space-2) var(--space-3)',
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: 'var(--radius-sm)',
                }}>
                  <div style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: session.status === 'validated' ? 'var(--success)' :
                               session.status === 'auto_tagged' ? 'var(--accent-primary)' :
                               session.status === 'extracting' ? 'var(--pending)' : 'var(--error)',
                    boxShadow: session.status === 'validated' ? '0 0 8px rgba(16,185,129,0.5)' :
                               session.status === 'extracting' ? '0 0 8px rgba(139,92,246,0.5)' : 'none',
                  }} />
                  <span style={{ flex: 1, fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                    {session.action}
                  </span>
                  <EmpireStatusPill
                    status={session.status === 'validated' ? 'success' :
                            session.status === 'auto_tagged' ? 'info' :
                            session.status === 'extracting' ? 'pending' : 'error'}
                    label={session.status.replace('_', ' ')}
                    size="sm"
                  />
                </div>
              ))}
            </div>

            <div style={{
              marginTop: 'var(--space-4)',
              padding: 'var(--space-3)',
              background: 'rgba(139,92,246,0.08)',
              border: '1px solid var(--accent-secondary-border)',
              borderRadius: 'var(--radius-md)',
            }}>
              <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--accent-secondary)', marginBottom: 'var(--space-2)' }}>
                Rule Example
              </p>
              <p style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                On 'checkout' page → Fill CVV → Submit
              </p>
            </div>
          </EmpireDataPanel>
        </div>

        {/* Bottom: Incident Learning */}
        <div style={{ marginTop: 'var(--space-4)' }}>
          <EmpireDataPanel title="Incident Learning" subtitle="Failure classification and fix validation" glass>
            <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
              <div style={{
                flex: 1,
                padding: 'var(--space-4)',
                background: 'rgba(239,68,68,0.1)',
                border: '1px solid var(--error-border)',
                borderRadius: 'var(--radius-lg)',
                textAlign: 'center',
              }}>
                <AlertTriangle size={24} style={{ color: 'var(--error)', marginBottom: 'var(--space-2)' }} />
                <p style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--error)' }}>7</p>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Classified Failures</p>
              </div>

              <div style={{
                flex: 1,
                padding: 'var(--space-4)',
                background: 'var(--success-bg)',
                border: '1px solid var(--success-border)',
                borderRadius: 'var(--radius-lg)',
                textAlign: 'center',
              }}>
                <CheckCircle size={24} style={{ color: 'var(--success)', marginBottom: 'var(--space-2)' }} />
                <p style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--success)' }}>12</p>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Validated Fixes</p>
              </div>

              <div style={{
                flex: 1,
                padding: 'var(--space-4)',
                background: 'rgba(245,158,11,0.1)',
                border: '1px solid var(--warning-border)',
                borderRadius: 'var(--radius-lg)',
                textAlign: 'center',
              }}>
                <Sparkles size={24} style={{ color: 'var(--warning)', marginBottom: 'var(--space-2)' }} />
                <p style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--warning)' }}>3</p>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Pending Skill Promotions</p>
              </div>
            </div>
          </EmpireDataPanel>
        </div>
      </div>
    </EmpireShell>
  );
}
