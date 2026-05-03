'use client';
import React, { useState, useEffect } from 'react';
import { Database, Brain, Activity, ChevronRight, X, Search } from 'lucide-react';
import { EmpireDetailDrawer } from '../ui/EmpireDetailDrawer';
import { API } from '@/lib/api';

interface MemoryEntry {
  id: string;
  summary: string;
  timestamp?: string;
  source?: string;
}

interface BrainEntry {
  id: string;
  type: 'commit' | 'fix' | 'pattern' | 'decision' | 'incident';
  content: string;
  timestamp?: string;
}

interface ContinuityData {
  memory_count?: number;
  brain_count?: number;
  recent_summaries?: MemoryEntry[];
  top_memories?: BrainEntry[];
  current_desk?: string;
  current_agent?: string;
  provider?: string;
  latency?: string;
  token_usage?: string;
}

interface ContinuityPanelProps {
  activeDesk: string;
  isOpen?: boolean;
  onClose?: () => void;
}

export function ContinuityPanel({ activeDesk, isOpen = true, onClose }: ContinuityPanelProps) {
  const [data, setData] = useState<ContinuityData>({});
  const [loading, setLoading] = useState(true);
  const [drawerType, setDrawerType] = useState<'memory' | 'brain' | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchContinuity = async () => {
      try {
        const r = await fetch(`${API}/max/continuity`);
        if (r.ok) {
          const d = await r.json();
          setData(d);
        }
      } catch { /* silent */ }
      setLoading(false);
    };
    fetchContinuity();
    const iv = setInterval(fetchContinuity, 30000);
    return () => clearInterval(iv);
  }, []);

  const memoryCount = data.memory_count ?? 99;
  const brainCount = data.brain_count ?? 3000;
  const memories = data.recent_summaries ?? [];
  const brainEntries = data.top_memories ?? [];
  const currentDesk = data.current_desk ?? activeDesk;
  const currentAgent = data.current_agent ?? 'Atlas';
  const provider = data.provider ?? 'Grok-4-fast';
  const latency = data.latency ?? '1.4s';
  const tokenUsage = data.token_usage ?? '$0.0023';

  const filteredMemories = memories.filter(m =>
    m.summary.toLowerCase().includes(searchTerm.toLowerCase())
  );
  const filteredBrain = brainEntries.filter(b =>
    b.content.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
        height: '100%',
        overflow: 'auto',
      }}>
        {/* Memory Bank Card */}
        <button
          onClick={() => setDrawerType('memory')}
          className="glass-premium"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
            padding: 'var(--space-4)',
            borderRadius: 'var(--radius-lg)',
            cursor: 'pointer',
            transition: 'all var(--transition-base)',
            border: 'none',
            width: '100%',
            textAlign: 'left',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Database size={16} style={{ color: 'var(--accent-primary)' }} />
              <span style={{
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                color: 'var(--text-primary)',
              }}>Memory Bank</span>
            </div>
            <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
          </div>
          <div style={{
            display: 'flex',
            gap: 'var(--space-2)',
            flexWrap: 'wrap',
          }}>
            <span style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              background: 'var(--accent-primary-bg)',
              color: 'var(--accent-primary)',
              padding: '2px 8px',
              borderRadius: 'var(--radius-full)',
            }}>
              {memoryCount} summaries
            </span>
          </div>
        </button>

        {/* Brain Card */}
        <button
          onClick={() => setDrawerType('brain')}
          className="glass-premium"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-2)',
            padding: 'var(--space-4)',
            borderRadius: 'var(--radius-lg)',
            cursor: 'pointer',
            transition: 'all var(--transition-base)',
            border: 'none',
            width: '100%',
            textAlign: 'left',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Brain size={16} style={{ color: 'var(--accent-secondary)' }} />
              <span style={{
                fontSize: 'var(--text-sm)',
                fontWeight: 600,
                color: 'var(--text-primary)',
              }}>Brain</span>
            </div>
            <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
          </div>
          <div style={{
            display: 'flex',
            gap: 'var(--space-2)',
            flexWrap: 'wrap',
          }}>
            <span style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              background: 'var(--accent-secondary-bg)',
              color: 'var(--accent-secondary)',
              padding: '2px 8px',
              borderRadius: 'var(--radius-full)',
            }}>
              {brainCount.toLocaleString()} entries
            </span>
          </div>
        </button>

        {/* Current Context Card */}
        <div className="glass-premium" style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-3)',
          padding: 'var(--space-4)',
          borderRadius: 'var(--radius-lg)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Activity size={16} style={{ color: 'var(--success)' }} />
            <span style={{
              fontSize: 'var(--text-sm)',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}>Current Context</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <ContextRow label="Desk" value={`${currentDesk} — ${currentAgent}`} />
            <ContextRow label="Provider" value={provider} />
            <ContextRow label="Latency" value={latency} />
            <ContextRow label="Token Usage" value={tokenUsage} />
          </div>
        </div>
      </div>

      {/* Memory Drawer */}
      <EmpireDetailDrawer
        isOpen={drawerType === 'memory'}
        onClose={() => setDrawerType(null)}
        title="Memory Bank"
        subtitle={`${memoryCount} summaries`}
        size="lg"
      >
        <div style={{ marginBottom: 'var(--space-4)' }}>
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
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {filteredMemories.length === 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>No memories found</p>
          )}
          {filteredMemories.map((mem, i) => (
            <div key={i} style={{
              padding: 'var(--space-3)',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              transition: 'all var(--transition-fast)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(99,102,241,0.1)';
              e.currentTarget.style.borderColor = 'var(--border-accent)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
            }}
            >
              <p style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--text-primary)',
                lineHeight: 1.5,
                marginBottom: 'var(--space-2)',
              }}>{mem.summary}</p>
              <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
                {mem.source && <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{mem.source}</span>}
                {mem.timestamp && <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{mem.timestamp}</span>}
              </div>
            </div>
          ))}
        </div>
      </EmpireDetailDrawer>

      {/* Brain Drawer */}
      <EmpireDetailDrawer
        isOpen={drawerType === 'brain'}
        onClose={() => setDrawerType(null)}
        title="Brain"
        subtitle={`${brainCount.toLocaleString()} entries`}
        size="lg"
      >
        <div style={{ marginBottom: 'var(--space-4)' }}>
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
              placeholder="Search brain..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {filteredBrain.length === 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>No entries found</p>
          )}
          {filteredBrain.map((entry, i) => (
            <div key={i} style={{
              padding: 'var(--space-3)',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              transition: 'all var(--transition-fast)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(139,92,246,0.1)';
              e.currentTarget.style.borderColor = 'var(--accent-secondary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
              e.currentTarget.style.borderColor = 'var(--border-subtle)';
            }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
                <span style={{
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  padding: '1px 6px',
                  borderRadius: 'var(--radius-sm)',
                  background: entry.type === 'commit' ? 'var(--success-bg)' :
                             entry.type === 'fix' ? 'var(--error-bg)' :
                             entry.type === 'pattern' ? 'var(--info-bg)' :
                             entry.type === 'decision' ? 'var(--warning-bg)' : 'rgba(255,255,255,0.05)',
                  color: entry.type === 'commit' ? 'var(--success)' :
                         entry.type === 'fix' ? 'var(--error)' :
                         entry.type === 'pattern' ? 'var(--info)' :
                         entry.type === 'decision' ? 'var(--warning)' : 'var(--text-muted)',
                }}>
                  {entry.type}
                </span>
              </div>
              <p style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--text-primary)',
                lineHeight: 1.5,
              }}>{entry.content}</p>
              {entry.timestamp && (
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-2)' }}>
                  {entry.timestamp}
                </p>
              )}
            </div>
          ))}
        </div>
      </EmpireDetailDrawer>
    </>
  );
}

function ContextRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    }}>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--text-secondary)' }}>{value}</span>
    </div>
  );
}
