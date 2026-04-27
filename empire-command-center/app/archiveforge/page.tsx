'use client';
import React, { useState, useEffect } from 'react';
import {
  Search, Package, CheckCircle, AlertCircle, Clock,
  ChevronRight, Image as ImageIcon, Upload, Edit, Send, Eye
} from 'lucide-react';
import { EmpireShell } from '../components/ui/EmpireShell';
import { EmpireDataPanel } from '../components/ui/EmpireDataPanel';
import { EmpireStatusPill } from '../components/ui/EmpireStatusPill';

const API = 'http://localhost:8000/api/v1';

interface Cover {
  id: string;
  title: string;
  reference?: string;
  status: 'pending' | 'live' | 'archived';
  thumbnail?: string;
}

interface Step {
  id: string;
  label: string;
  status: 'done' | 'active' | 'pending';
}

const STEPS: Step[] = [
  { id: 'upload', label: 'Upload', status: 'done' },
  { id: 'intake', label: 'Intake', status: 'done' },
  { id: 'review', label: 'Review', status: 'active' },
  { id: 'rebox', label: 'Rebox', status: 'pending' },
  { id: 'publish', label: 'Publish', status: 'pending' },
  { id: 'marketforge', label: 'MarketForge', status: 'pending' },
];

const DEFAULT_COVERS: Cover[] = [
  { id: '1', title: 'TIME Magazine 1965', reference: '#6366f1', status: 'pending' },
  { id: '2', title: 'Life Cover 1972', reference: '#8b5cf6', status: 'live' },
  { id: '3', title: 'National Geographic 1988', reference: '#10b981', status: 'live' },
  { id: '4', title: 'Newsweek 1995', reference: '#f59e0b', status: 'archived' },
  { id: '5', title: 'Vogue 2000', reference: '#ef4444', status: 'pending' },
  { id: '6', title: 'Rolling Stone 1975', reference: '#6366f1', status: 'live' },
];

const INVENTORY = [
  { location: 'Shelf A-1', capacity: 120, occupancy: 89 },
  { location: 'Shelf A-2', capacity: 120, occupancy: 67 },
  { location: 'Shelf B-1', capacity: 80, occupancy: 80 },
  { location: 'Shelf B-2', capacity: 80, occupancy: 11 },
];

export default function ArchiveForgePage() {
  const [covers, setCovers] = useState<Cover[]>([]);
  const [selectedCover, setSelectedCover] = useState<Cover | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/archiveforge/covers`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d?.covers) setCovers(d.covers);
        else setCovers(DEFAULT_COVERS);
      })
      .catch(() => setCovers(DEFAULT_COVERS))
      .finally(() => setLoading(false));
  }, []);

  const pendingCount = covers.filter(c => c.status === 'pending').length;
  const liveCount = covers.filter(c => c.status === 'live').length;
  const archivedCount = covers.filter(c => c.status === 'archived').length;

  return (
    <EmpireShell commitHash="f535d53">
      <div className="animated-gradient" style={{ padding: 'var(--space-6)' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 2fr 1fr',
          gap: 'var(--space-4)',
          height: 'calc(100vh - var(--topbar-height) - var(--space-12))',
          minHeight: 600,
        }}>
          {/* Left: Review & Publish */}
          <EmpireDataPanel title="Review & Publish" subtitle="LIFE Cover Workflow" glass>
            {/* Progress Stepper */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
              {STEPS.map((step, i) => (
                <div key={step.id} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <div style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: step.status === 'done'
                      ? 'var(--success)'
                      : step.status === 'active'
                        ? 'var(--accent-primary)'
                        : 'rgba(255,255,255,0.08)',
                    boxShadow: step.status === 'active'
                      ? '0 0 20px rgba(99,102,241,0.5)'
                      : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    {step.status === 'done' ? (
                      <CheckCircle size={14} color="#fff" />
                    ) : step.status === 'active' ? (
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#fff' }} />
                    ) : (
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{i + 1}</span>
                    )}
                  </div>
                  <span style={{
                    fontSize: 'var(--text-sm)',
                    fontWeight: step.status === 'active' ? 600 : 400,
                    color: step.status === 'done'
                      ? 'var(--success)'
                      : step.status === 'active'
                        ? 'var(--text-primary)'
                        : 'var(--text-muted)',
                  }}>
                    {step.label}
                  </span>
                  {step.status !== 'done' && (
                    <ChevronRight size={14} style={{ color: 'var(--text-muted)', marginLeft: 'auto' }} />
                  )}
                </div>
              ))}
            </div>

            {/* Checklist */}
            <div style={{
              padding: 'var(--space-3)',
              background: 'rgba(255,255,255,0.04)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
            }}>
              <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>
                Checklist
              </p>
              {[
                { text: 'Personal effects removed', done: true },
                { text: 'Approval status', done: true },
                { text: 'Quality check', done: false },
                { text: 'MarketForge sync', done: false },
              ].map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                  <CheckCircle size={14} style={{ color: item.done ? 'var(--success)' : 'var(--text-muted)' }} />
                  <span style={{ fontSize: 'var(--text-xs)', color: item.done ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                    {item.text}
                  </span>
                </div>
              ))}
            </div>
          </EmpireDataPanel>

          {/* Center: LIFE Cover Search */}
          <EmpireDataPanel
            title="LIFE Cover Search"
            subtitle={`${covers.length} covers indexed`}
            glass
            actions={[
              { label: 'Upload', onClick: () => {}, variant: 'primary' as const },
            ]}
          >
            {/* Search */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-2) var(--space-3)',
              marginBottom: 'var(--space-4)',
            }}>
              <Search size={14} style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search covers..."
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

            {/* Cover Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 'var(--space-3)',
              overflowY: 'auto',
              maxHeight: 400,
            }}>
              {(loading ? DEFAULT_COVERS : covers).map((cover) => (
                <div
                  key={cover.id}
                  onClick={() => setSelectedCover(cover)}
                  className="glass-premium"
                  style={{
                    padding: 'var(--space-3)',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    border: selectedCover?.id === cover.id
                      ? '2px solid var(--accent-primary)'
                      : '2px solid transparent',
                    boxShadow: selectedCover?.id === cover.id
                      ? '0 0 25px rgba(99,102,241,0.4)'
                      : 'none',
                    transition: 'all var(--transition-base)',
                  }}
                  onMouseEnter={(e) => {
                    if (selectedCover?.id !== cover.id) {
                      e.currentTarget.style.transform = 'scale(1.03)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'scale(1)';
                  }}
                >
                  <div style={{
                    height: 80,
                    background: 'rgba(255,255,255,0.05)',
                    borderRadius: 'var(--radius-sm)',
                    marginBottom: 'var(--space-2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}>
                    <ImageIcon size={24} style={{ color: 'var(--text-muted)' }} />
                  </div>
                  <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                    {cover.title}
                  </p>
                  {cover.reference && (
                    <p style={{ fontSize: '10px', color: cover.reference.startsWith('#6366') ? 'var(--accent-primary)' : 'var(--text-muted)' }}>
                      Ref {cover.reference}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </EmpireDataPanel>

          {/* Right: MarketForge Queue */}
          <EmpireDataPanel title="MarketForge Queue" subtitle="Publishing status" glass>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              {[
                { label: 'Pending', count: pendingCount, color: 'warning' },
                { label: 'Live', count: liveCount, color: 'info' },
                { label: 'Archived', count: archivedCount, color: 'muted' },
              ].map((group) => (
                <div key={group.label} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: 'var(--space-3)',
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: 'var(--radius-md)',
                }}>
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{group.label}</span>
                  <EmpireStatusPill
                    status={group.color as any}
                    label={group.count.toString()}
                    size="sm"
                  />
                </div>
              ))}
            </div>

            <div style={{ marginTop: 'var(--space-4)' }}>
              <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>
                Recent Queue
              </p>
              {covers.slice(0, 4).map((cover) => (
                <div key={cover.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: 'var(--space-2) 0',
                  borderBottom: '1px solid var(--border-subtle)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <ImageIcon size={12} style={{ color: 'var(--text-muted)' }} />
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{cover.title}</span>
                  </div>
                  <EmpireStatusPill
                    status={cover.status === 'live' ? 'info' : cover.status === 'pending' ? 'warning' : 'neutral'}
                    label={cover.status}
                    size="sm"
                  />
                </div>
              ))}
            </div>
          </EmpireDataPanel>
        </div>

        {/* Bottom: Inventory Management */}
        <div style={{ marginTop: 'var(--space-4)' }}>
          <EmpireDataPanel title="Inventory Management" subtitle="247 items archived · 89 published" glass>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 'var(--space-4)',
            }}>
              {INVENTORY.map((inv) => (
                <div key={inv.location} className="glass-premium" style={{
                  padding: 'var(--space-4)',
                  borderRadius: 'var(--radius-md)',
                  textAlign: 'center',
                }}>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>
                    {inv.location}
                  </p>
                  <div style={{
                    height: 4,
                    background: 'rgba(255,255,255,0.1)',
                    borderRadius: 'var(--radius-full)',
                    marginBottom: 'var(--space-2)',
                    overflow: 'hidden',
                  }}>
                    <div style={{
                      width: `${(inv.occupancy / inv.capacity) * 100}%`,
                      height: '100%',
                      background: inv.occupancy === inv.capacity
                        ? 'var(--warning)'
                        : 'var(--accent-primary)',
                      borderRadius: 'var(--radius-full)',
                    }} />
                  </div>
                  <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {inv.occupancy}/{inv.capacity}
                  </p>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Occupied</p>
                </div>
              ))}
            </div>
          </EmpireDataPanel>
        </div>
      </div>
    </EmpireShell>
  );
}
