'use client';
import { useState } from 'react';
import { FlaskConical, Zap, CheckCircle2, Clock, Eye } from 'lucide-react';
import { StatsBar, FilterTabs, StatusBadge, TaskList } from './shared';

type ExpStatus = 'running' | 'completed' | 'failed' | 'planned';

interface Experiment {
  id: string;
  name: string;
  description: string;
  status: ExpStatus;
  category: string;
  startedAt: string;
  result?: string;
}

const STATUS_COLOR: Record<ExpStatus, string> = {
  running: '#f59e0b',
  completed: '#22c55e',
  failed: '#ef4444',
  planned: '#8B5CF6',
};

const MOCK_EXPERIMENTS: Experiment[] = [
  {
    id: 'e1', name: 'xAI Vision Window Measurement',
    description: 'Test Grok vision API for extracting window dimensions from photos',
    status: 'completed', category: 'AI Vision', startedAt: '2026-02-20',
    result: 'Accuracy: ~85% within 2 inches. Needs reference object for scale.',
  },
  {
    id: 'e2', name: 'Voice-to-Task Pipeline',
    description: 'Transcribe voice memos via xAI and auto-create tasks with desk routing',
    status: 'planned', category: 'AI Voice', startedAt: '',
  },
  {
    id: 'e3', name: 'Auto Quote from Photo',
    description: 'Photo → measurements → treatment suggestion → quote generation pipeline',
    status: 'running', category: 'Automation', startedAt: '2026-02-24',
  },
  {
    id: 'e4', name: 'Smart Follow-up Drafter',
    description: 'Generate personalized follow-up emails based on client history and lead stage',
    status: 'completed', category: 'AI Text', startedAt: '2026-02-18',
    result: 'Good quality with Claude. Needs human review for tone.',
  },
  {
    id: 'e5', name: 'Fabric Pattern Match',
    description: 'Use vision AI to find similar fabrics from swatch photos',
    status: 'planned', category: 'AI Vision', startedAt: '',
  },
  {
    id: 'e6', name: 'Automated Instagram Captions',
    description: 'Generate engaging captions from before/after project photos',
    status: 'failed', category: 'AI Text', startedAt: '2026-02-22',
    result: 'Captions too generic. Need fine-tuned prompt per treatment type.',
  },
];

export default function LabDesk() {
  const [experiments] = useState<Experiment[]>(MOCK_EXPERIMENTS);
  const [filter, setFilter] = useState<string>('all');

  const running = experiments.filter(e => e.status === 'running').length;
  const completed = experiments.filter(e => e.status === 'completed').length;
  const planned = experiments.filter(e => e.status === 'planned').length;
  const filtered = filter === 'all' ? experiments : experiments.filter(e => e.status === filter);

  return (
    <div className="flex flex-col h-full">
      <StatsBar items={[
        { label: 'Running', value: String(running), icon: Zap, color: '#f59e0b' },
        { label: 'Completed', value: String(completed), icon: CheckCircle2, color: '#22c55e' },
        { label: 'Planned', value: String(planned), icon: Clock, color: '#8B5CF6' },
      ]} />

      <FilterTabs options={['all', 'running', 'completed', 'planned', 'failed']} active={filter} onChange={setFilter} />

      <div className="flex-1 overflow-auto p-4 flex gap-4">
        <div className="flex-1 flex flex-col gap-4">
          <div className="space-y-3">
            {filtered.map(exp => (
              <div
                key={exp.id}
                className="rounded-xl p-4 transition"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--hover)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'var(--surface)')}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <FlaskConical className="w-4 h-4" style={{ color: '#E11D48' }} />
                    <StatusBadge label={exp.status} color={STATUS_COLOR[exp.status]} />
                    <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{exp.category}</span>
                  </div>
                  {exp.startedAt && (
                    <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{exp.startedAt}</span>
                  )}
                </div>
                <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>{exp.name}</p>
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{exp.description}</p>
                {exp.result && (
                  <div className="mt-3 rounded-lg p-2.5" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
                    <p className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--gold)' }}>Result</p>
                    <p className="text-xs" style={{ color: 'var(--text-primary)' }}>{exp.result}</p>
                  </div>
                )}
              </div>
            ))}
            {filtered.length === 0 && (
              <p className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>No experiments match filter</p>
            )}
          </div>
          <TaskList desk="lab" compact />
        </div>
      </div>
    </div>
  );
}
