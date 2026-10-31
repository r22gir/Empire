'use client';
import { useCallback, useEffect, useState } from 'react';
import { API } from '../../../lib/api';
import {
  AlertTriangle, CheckCircle2, Circle, FileText, Loader2, Lock, ShieldCheck,
} from 'lucide-react';

interface StageRow {
  key?: string;
  stage_key: string;
  title: string;
  description: string;
  status: string;
  required: boolean;
  conditional?: boolean;
  approved_by?: string | null;
  approved_at?: string | null;
  linked_documents?: string[];
  gate?: boolean;
  order?: number;
}

interface ChecklistPayload {
  job_id: string;
  title?: string;
  current_stage_key?: string | null;
  current_stage_title?: string;
  current_status?: string;
  missing?: string[];
  next_step?: string;
  gate_open?: boolean;
  stages?: StageRow[];
}

const STATUS_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  not_started: { bg: '#f3f4f6', text: '#6b7280', label: 'Not started' },
  drafted: { bg: '#fffbeb', text: '#b45309', label: 'Drafted' },
  approved: { bg: '#ecfdf5', text: '#047857', label: 'Approved' },
  done: { bg: '#eff6ff', text: '#1d4ed8', label: 'Done' },
};

export default function JobStageChecklist({ jobId }: { jobId: string }) {
  const [data, setData] = useState<ChecklistPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [gateMessage, setGateMessage] = useState('');

  const load = useCallback(() => {
    if (!jobId) return;
    setLoading(true);
    fetch(`${API}/jobs/${jobId}/stages`)
      .then((res) => res.json())
      .then((payload) => {
        setData(payload);
        setError(payload.detail || payload.error ? String(payload.detail || payload.error) : '');
      })
      .catch(() => setError('Could not load document-set checklist.'))
      .finally(() => setLoading(false));
  }, [jobId]);

  useEffect(() => { load(); }, [load]);

  const approveWorkroom = async () => {
    setBusy('approve');
    setGateMessage('');
    try {
      const res = await fetch(`${API}/jobs/${jobId}/stages/workroom_approval/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_by: 'workroom' }),
      });
      const payload = await res.json();
      if (!res.ok) {
        setGateMessage(payload.detail || payload.error || 'Approval failed.');
      }
      load();
    } catch {
      setGateMessage('Approval failed.');
    } finally {
      setBusy('');
    }
  };

  const generateEstimate = async () => {
    setBusy('estimate');
    setGateMessage('');
    try {
      const res = await fetch(`${API}/jobs/${jobId}/estimates/client`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lines: [
            { area: 'Living Room', category: 'Labor', description: 'Workroom labor', qty: 1, unit_price: 100 },
            { area: 'Living Room', category: 'Materials', description: 'Lining', qty: 2, unit_price: 40 },
            { area: 'Living Room', category: 'Install', description: 'Install', qty: 1, unit_price: 95 },
          ],
        }),
      });
      const payload = await res.json();
      if (!res.ok || payload.blocked || payload.error === 'WORKROOM_APPROVAL_REQUIRED') {
        setGateMessage(
          payload.next_step ||
          payload.detail ||
          'Workroom approval (stage 4) must be approved before a client estimate can be generated.',
        );
      } else {
        setGateMessage('Client + INTERNAL estimates drafted. Nothing was sent.');
        load();
      }
    } catch {
      setGateMessage('Estimate request failed.');
    } finally {
      setBusy('');
    }
  };

  if (!jobId) return null;

  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#888', letterSpacing: 0.6, marginBottom: 8 }}>
        DOCUMENT SET
      </div>
      {loading && (
        <div style={{ fontSize: 12, color: '#888', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Loader2 size={12} className="animate-spin" /> Loading checklist…
        </div>
      )}
      {error && !data?.stages && (
        <div style={{ fontSize: 12, color: '#b45309' }}>{error}</div>
      )}
      {data?.stages && (
        <>
          <div style={{
            background: data.gate_open ? '#ecfdf5' : '#fff7ed',
            border: `1px solid ${data.gate_open ? '#a7f3d0' : '#fed7aa'}`,
            borderRadius: 8, padding: 10, marginBottom: 10, fontSize: 11,
          }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>
              {data.current_stage_title || 'Complete'} · {(data.current_status || '').replace('_', ' ')}
            </div>
            <div style={{ color: '#555' }}>{data.next_step}</div>
            {(data.missing || []).length > 0 && (
              <div style={{ marginTop: 6, color: '#9a3412' }}>
                {(data.missing || []).map((item) => <div key={item}>• {item}</div>)}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(data.stages || []).map((stage) => {
              if (stage.conditional && !stage.required) {
                return (
                  <div key={stage.stage_key} style={{
                    fontSize: 11, color: '#aaa', padding: '6px 8px',
                    border: '1px dashed #e5e2dc', borderRadius: 8,
                  }}>
                    {stage.order}. {stage.title} — not required
                  </div>
                );
              }
              const tone = STATUS_STYLE[stage.status] || STATUS_STYLE.not_started;
              const current = data.current_stage_key === stage.stage_key;
              return (
                <div key={stage.stage_key} style={{
                  border: `1px solid ${current ? '#b8960c' : '#ece8e0'}`,
                  background: current ? '#fdf8eb' : '#fff',
                  borderRadius: 8, padding: 8, fontSize: 11,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ fontWeight: 700 }}>
                      {stage.order}. {stage.title}
                    </div>
                    <span style={{
                      background: tone.bg, color: tone.text, borderRadius: 99,
                      padding: '1px 8px', fontSize: 10, fontWeight: 700,
                    }}>{tone.label}</span>
                  </div>
                  <div style={{ color: '#666', marginTop: 3 }}>{stage.description}</div>
                  {stage.approved_by && (
                    <div style={{ color: '#047857', marginTop: 4 }}>
                      Approved by {stage.approved_by}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10 }}>
            <button
              onClick={approveWorkroom}
              disabled={busy === 'approve' || !!data.gate_open}
              style={{
                fontSize: 10, padding: '6px 10px', border: 'none', borderRadius: 6,
                background: data.gate_open ? '#d1fae5' : '#111', color: data.gate_open ? '#065f46' : '#fff',
                fontWeight: 700, cursor: data.gate_open ? 'default' : 'pointer',
                display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              {busy === 'approve' ? <Loader2 size={11} className="animate-spin" /> : <ShieldCheck size={11} />}
              {data.gate_open ? 'Stage 4 approved' : 'Approve workroom doc'}
            </button>
            <button
              onClick={generateEstimate}
              disabled={busy === 'estimate'}
              data-testid="generate-client-estimate"
              style={{
                fontSize: 10, padding: '6px 10px', border: 'none', borderRadius: 6,
                background: data.gate_open ? '#b8960c' : '#7f1d1d', color: '#fff',
                fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              {busy === 'estimate' ? <Loader2 size={11} className="animate-spin" /> : data.gate_open ? <FileText size={11} /> : <Lock size={11} />}
              Generate client estimate
            </button>
          </div>
          {gateMessage && (
            <div data-testid="estimate-gate-message" style={{
              marginTop: 8, fontSize: 11, padding: 8, borderRadius: 8,
              background: data.gate_open ? '#ecfdf5' : '#fef2f2',
              color: data.gate_open ? '#065f46' : '#991b1b',
              display: 'flex', gap: 6, alignItems: 'flex-start',
            }}>
              {data.gate_open ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
              <span>{gateMessage}</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function StageDot({ status }: { status?: string }) {
  if (status === 'done' || status === 'approved') return <CheckCircle2 size={12} color="#047857" />;
  if (status === 'drafted') return <Circle size={12} color="#b45309" />;
  return <Circle size={12} color="#d1d5db" />;
}
