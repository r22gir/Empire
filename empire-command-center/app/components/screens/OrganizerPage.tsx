'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle, CheckCircle2, ClipboardList, CreditCard, DollarSign,
  FileText, MessageSquare, Plus, Scale, Scissors, Shield, Smartphone,
} from 'lucide-react';
import { API } from '../../lib/api';

type Tab = 'jobs' | 'rules' | 'drafts' | 'pay' | 'costing' | 'credits' | 'family';

interface OrganizerJob {
  id: string;
  job_number: string;
  quote_number?: string;
  customer_name?: string;
  status: string;
  style?: string;
  fabric_codes?: string[];
  photos?: string[];
  seamstress_hours?: number;
  seamstress_pay?: number;
  due_date?: string;
  quoted_amount?: number;
  business_unit?: string;
  items?: JobItem[];
}

interface JobItem {
  id: string;
  style?: string;
  fabric_code?: string;
  room?: string;
  description?: string;
  seamstress_hours?: number;
  seamstress_pay?: number;
  measurements?: Record<string, { display?: string }>;
  photos?: string[];
}

interface Draft {
  id: string;
  channel: string;
  status: string;
  body: string;
  subject?: string;
  job_id?: string;
  source?: string;
  approved_by?: string;
}

interface RuleRow {
  id: string;
  name: string;
  trigger_event: string;
  action: string;
  enabled: boolean;
}

interface AlertRow {
  id: string;
  requester?: string;
  requester_agent?: string;
  summary: string;
  classification: string;
  delivery_status: string;
  recipient_role: string;
  noop_reason?: string;
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'jobs', label: 'Work Orders' },
  { id: 'rules', label: 'Rules' },
  { id: 'drafts', label: 'Drafts' },
  { id: 'pay', label: 'Text-to-Pay' },
  { id: 'costing', label: 'Job Costing' },
  { id: 'credits', label: 'Credits' },
  { id: 'family', label: 'Family Alerts' },
];

const SAMPLE_QUOTE = {
  id: 'demo-approved-quote',
  quote_number: 'EST-2026-0888',
  status: 'approved',
  customer_name: 'Ada Client',
  customer_id: 'cust-ada',
  business_unit: 'workroom',
  project_name: 'Primary bedroom panels',
  total: 4200,
  due_date: '2026-11-02',
  photos: ['/uploads/quote/east-window.jpg'],
  line_items: [
    {
      item_type: 'drapery',
      item_style: 'pinch pleat',
      description: 'East window panels',
      room: 'Primary Bedroom',
      fabric_code: 'Kravet V639 Navy Velvet',
      width: 84.5,
      height: 96.25,
      labor_hours: 8,
      labor_rate: 45,
      labor_total: 360,
      quantity: 1,
      photos: ['/uploads/quote/east-window.jpg'],
    },
  ],
};

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Organizer API ${res.status}: ${path}`);
  return res.json();
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Organizer API ${res.status}: ${path}`);
  return data as T;
}

function money(value?: number | null) {
  return `$${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function Pill({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 999,
      background: `${color}18`, color, textTransform: 'uppercase', letterSpacing: 0.3,
    }}>
      {label}
    </span>
  );
}

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16, ...style,
    }}>
      {children}
    </div>
  );
}

export default function OrganizerPage() {
  const [tab, setTab] = useState<Tab>('jobs');
  const [jobs, setJobs] = useState<OrganizerJob[]>([]);
  const [draftRows, setDraftRows] = useState<Draft[]>([]);
  const [ruleRows, setRuleRows] = useState<RuleRow[]>([]);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [selectedJob, setSelectedJob] = useState<OrganizerJob | null>(null);
  const [costing, setCosting] = useState<any>(null);
  const [credits, setCredits] = useState<any>(null);
  const [familyStatus, setFamilyStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [quoteJson, setQuoteJson] = useState(JSON.stringify(SAMPLE_QUOTE, null, 2));
  const [payChannel, setPayChannel] = useState<'sms' | 'whatsapp'>('sms');
  const [creditForm, setCreditForm] = useState({ customer_id: 'cust-ada', amount: '150', reason: 'Deposit adjustment', invoice_id: 'INV-2026-010' });
  const [familyForm, setFamilyForm] = useState({ requester: 'juan', message: 'Pedir ayuda a Max — need a fix on the measurement drawing' });
  const [actualLabor, setActualLabor] = useState('380');
  const [actualMaterials, setActualMaterials] = useState('2100');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dash, jobsRes, draftsRes, rulesRes, alertsRes] = await Promise.all([
        fetchJson<any>('/sprint-m/dashboard'),
        fetchJson<{ jobs: OrganizerJob[] }>('/sprint-m/jobs'),
        fetchJson<{ drafts: Draft[] }>('/sprint-m/drafts'),
        fetchJson<{ rules: RuleRow[] }>('/sprint-m/rules'),
        fetchJson<{ alerts: AlertRow[]; status: any }>('/sprint-m/family-alerts'),
      ]);
      setJobs(jobsRes.jobs || []);
      setDraftRows(draftsRes.drafts || []);
      setRuleRows(rulesRes.rules || []);
      setAlerts(alertsRes.alerts || []);
      setFamilyStatus(alertsRes.status || dash.family_alert_status);
      if (!selectedJob && jobsRes.jobs?.[0]) setSelectedJob(jobsRes.jobs[0]);
    } catch (exc: any) {
      setError(exc?.message || 'Organizer unavailable');
    } finally {
      setLoading(false);
    }
  }, [selectedJob]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!selectedJob) return;
    fetchJson(`/sprint-m/jobs/${selectedJob.id}/costing`).then(setCosting).catch(() => setCosting(null));
    if (selectedJob.customer_name) {
      const customerId = creditForm.customer_id || 'cust-ada';
      fetchJson(`/sprint-m/credits/${customerId}`).then(setCredits).catch(() => {});
    }
  }, [selectedJob, creditForm.customer_id]);

  const pendingDrafts = useMemo(() => draftRows.filter(d => d.status === 'draft'), [draftRows]);

  const convertQuote = async () => {
    setNotice(null);
    setError(null);
    try {
      const quote = JSON.parse(quoteJson);
      const result = await postJson<any>('/sprint-m/work-orders/from-quote', { quote });
      setNotice(`Work order ${result.job.job_number} created. Fabric stored as internal codes only.`);
      setSelectedJob(result.job);
      await load();
    } catch (exc: any) {
      setError(exc?.message || 'Convert failed');
    }
  };

  const scheduleSelected = async () => {
    if (!selectedJob) return;
    setError(null);
    try {
      const result = await postJson<any>(`/sprint-m/jobs/${selectedJob.id}/schedule`, {});
      setNotice('Job scheduled. A client email draft was queued — Max did not send it.');
      setSelectedJob(result.job);
      await load();
    } catch (exc: any) {
      setError(exc?.message || 'Schedule failed');
    }
  };

  const createPayDraft = async () => {
    if (!selectedJob) return;
    setError(null);
    try {
      const result = await postJson<any>(`/sprint-m/jobs/${selectedJob.id}/text-to-pay`, { channel: payChannel });
      setNotice(`${payChannel.toUpperCase()} draft created with a non-expiring ${result.payment_link.brand} link. Owner approval required.`);
      await load();
    } catch (exc: any) {
      setError(exc?.message || 'Text-to-pay failed');
    }
  };

  const approveDraft = async (id: string) => {
    setError(null);
    try {
      await postJson(`/sprint-m/drafts/${id}/approve`, {});
      setNotice('Draft approved. Max still will not send it to the client.');
      await load();
    } catch (exc: any) {
      setError(exc?.message || 'Approve failed');
    }
  };

  const trySend = async (id: string) => {
    setError(null);
    try {
      await postJson(`/sprint-m/drafts/${id}/send`, {});
    } catch (exc: any) {
      setNotice(exc?.message || 'Max never sends to clients.');
    }
  };

  const addActuals = async () => {
    if (!selectedJob) return;
    setError(null);
    try {
      await postJson(`/sprint-m/jobs/${selectedJob.id}/costing`, {
        category: 'labor', description: 'Actual seamstress hours', planned_amount: 0, actual_amount: Number(actualLabor),
      });
      await postJson(`/sprint-m/jobs/${selectedJob.id}/costing`, {
        category: 'materials', description: 'Actual fabric & supplies', planned_amount: 0, actual_amount: Number(actualMaterials),
      });
      const next = await fetchJson(`/sprint-m/jobs/${selectedJob.id}/costing`);
      setCosting(next);
      setNotice('Actuals recorded. Margin updated.');
    } catch (exc: any) {
      setError(exc?.message || 'Costing update failed');
    }
  };

  const createMemo = async () => {
    setError(null);
    try {
      const result = await postJson('/sprint-m/credits/memos', {
        customer_id: creditForm.customer_id,
        customer_name: selectedJob?.customer_name || 'Ada Client',
        amount: Number(creditForm.amount),
        reason: creditForm.reason,
      });
      setCredits(result);
      setNotice('Credit memo posted to the client account.');
    } catch (exc: any) {
      setError(exc?.message || 'Credit memo failed');
    }
  };

  const applyCredit = async () => {
    setError(null);
    try {
      const result = await postJson(`/sprint-m/credits/${creditForm.customer_id}/apply`, {
        invoice_id: creditForm.invoice_id,
      });
      setCredits(result);
      setNotice(`Applied ${money(result.last_application?.amount)} to ${creditForm.invoice_id}.`);
    } catch (exc: any) {
      setError(exc?.message || 'Apply credit failed');
    }
  };

  const submitFamily = async () => {
    setError(null);
    try {
      const result = await postJson<any>('/sprint-m/family-help', familyForm);
      setNotice(`${result.delivery_status === 'noop' ? 'No-op alert recorded' : 'Owner alert queued'} for Rafael only (${result.classification}).`);
      await load();
    } catch (exc: any) {
      setError(exc?.message || 'Family help failed');
    }
  };

  return (
    <div style={{ padding: '20px 24px', overflow: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, gap: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: '#dcfce7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <ClipboardList size={18} color="#16a34a" />
            </div>
            <div>
              <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Organizer</h2>
              <p style={{ fontSize: 12, color: '#888', margin: 0 }}>Sprint M — approved quotes become jobs. Max drafts only. Owner sends.</p>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Pill label="Drafts never auto-send" color="#b8960c" />
          <Pill label="V###-Color only" color="#16a34a" />
          <Pill label="Fractions" color="#2563eb" />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10, marginBottom: 16 }}>
        {[
          { label: 'Jobs', value: jobs.length, color: '#16a34a', icon: <Scissors size={14} /> },
          { label: 'Pending drafts', value: pendingDrafts.length, color: '#b8960c', icon: <MessageSquare size={14} /> },
          { label: 'Rules', value: ruleRows.length, color: '#2563eb', icon: <Shield size={14} /> },
          { label: 'Family alerts', value: alerts.length, color: '#7c3aed', icon: <AlertTriangle size={14} /> },
        ].map(kpi => (
          <Card key={kpi.label} style={{ padding: '12px 14px' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#888', textTransform: 'uppercase', display: 'flex', gap: 6, alignItems: 'center' }}>
              {kpi.icon} {kpi.label}
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </Card>
        ))}
      </div>

      {notice && (
        <div style={{ marginBottom: 12, padding: '10px 12px', borderRadius: 10, background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', fontSize: 12 }}>
          {notice}
        </div>
      )}
      {error && (
        <div style={{ marginBottom: 12, padding: '10px 12px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', fontSize: 12 }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
        {TABS.map(item => (
          <button key={item.id} onClick={() => setTab(item.id)} style={{
            fontSize: 11, padding: '6px 12px', borderRadius: 999, cursor: 'pointer', fontWeight: tab === item.id ? 700 : 500,
            border: tab === item.id ? '1.5px solid #16a34a' : '1px solid #e5e2dc',
            background: tab === item.id ? '#f0fdf4' : '#fff', color: tab === item.id ? '#166534' : '#555',
          }}>
            {item.label}
          </button>
        ))}
      </div>

      {loading && <div style={{ fontSize: 12, color: '#999' }}>Loading Organizer…</div>}

      {tab === 'jobs' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) minmax(320px, 1.1fr)', gap: 14 }}>
          <Card>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Approved quote → work order</div>
            <p style={{ fontSize: 12, color: '#666', marginTop: 0 }}>
              Fabric is stored as internal <code>V###-Color</code> only. Brand and supplier names are stripped. Measurements become fractions.
            </p>
            <textarea value={quoteJson} onChange={e => setQuoteJson(e.target.value)}
              style={{ width: '100%', minHeight: 220, fontSize: 11, fontFamily: 'ui-monospace, monospace', border: '1px solid #e5e2dc', borderRadius: 8, padding: 8 }} />
            <button onClick={convertQuote} style={primaryBtn}>
              <Plus size={12} /> Create Organizer job
            </button>
          </Card>
          <div>
            <Card style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 700, marginBottom: 10 }}>Jobs</div>
              {jobs.length === 0 && <div style={{ fontSize: 12, color: '#aaa' }}>No Organizer jobs yet.</div>}
              {jobs.map(job => (
                <button key={job.id} onClick={() => setSelectedJob(job)} style={{
                  width: '100%', textAlign: 'left', padding: 10, marginBottom: 8, borderRadius: 10, cursor: 'pointer',
                  border: selectedJob?.id === job.id ? '1.5px solid #16a34a' : '1px solid #ece8e0',
                  background: selectedJob?.id === job.id ? '#f0fdf4' : '#faf9f6',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <strong style={{ fontSize: 13 }}>{job.job_number}</strong>
                    <Pill label={job.status} color={job.status === 'sold' ? '#16a34a' : '#2563eb'} />
                  </div>
                  <div style={{ fontSize: 12, color: '#555', marginTop: 4 }}>{job.customer_name} · {job.style || '—'}</div>
                  <div style={{ fontSize: 11, color: '#888' }}>{(job.fabric_codes || []).join(', ') || 'No fabric code'} · due {job.due_date || '—'}</div>
                </button>
              ))}
            </Card>
            {selectedJob && (
              <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <strong>{selectedJob.job_number}</strong>
                  <button onClick={scheduleSelected} style={ghostBtn}>Mark scheduled</button>
                </div>
                <div style={{ fontSize: 12, color: '#555', display: 'grid', gap: 4 }}>
                  <div>Style: {selectedJob.style || '—'}</div>
                  <div>Fabric: {(selectedJob.fabric_codes || []).join(', ') || '—'}</div>
                  <div>Seamstress: {selectedJob.seamstress_hours || 0}h / {money(selectedJob.seamstress_pay)}</div>
                  <div>Due: {selectedJob.due_date || '—'} · Photos: {(selectedJob.photos || []).length}</div>
                </div>
                {(selectedJob.items || []).map(item => (
                  <div key={item.id} style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #f0ece4', fontSize: 12 }}>
                    <div style={{ fontWeight: 600 }}>{item.room} · {item.style}</div>
                    <div style={{ color: '#666' }}>{item.fabric_code || 'no fabric'} · {item.description}</div>
                    <div style={{ color: '#888' }}>
                      {Object.entries(item.measurements || {}).map(([k, v]) => `${k} ${v.display}`).join(' · ')}
                    </div>
                  </div>
                ))}
              </Card>
            )}
          </div>
        </div>
      )}

      {tab === 'rules' && (
        <Card>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Owner-defined trigger rules</div>
          <p style={{ fontSize: 12, color: '#666' }}>Examples: proposal signed → job Sold; job scheduled → draft client email. Outbound messages stay drafts.</p>
          {ruleRows.map(rule => (
            <div key={rule.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #f0ece4', fontSize: 13 }}>
              <div>
                <div style={{ fontWeight: 600 }}>{rule.name}</div>
                <div style={{ fontSize: 11, color: '#888' }}>{rule.trigger_event} → {rule.action}</div>
              </div>
              <Pill label={rule.enabled ? 'on' : 'off'} color={rule.enabled ? '#16a34a' : '#999'} />
            </div>
          ))}
        </Card>
      )}

      {tab === 'drafts' && (
        <Card>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Outbound drafts</div>
          <p style={{ fontSize: 12, color: '#666' }}>Max never sends to clients. Owner approves, then sends from their own phone or mail client.</p>
          {draftRows.length === 0 && <div style={{ fontSize: 12, color: '#aaa' }}>No drafts yet.</div>}
          {draftRows.map(draft => (
            <div key={draft.id} style={{ padding: '12px 0', borderBottom: '1px solid #f0ece4' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
                <div>
                  <strong style={{ fontSize: 13 }}>{draft.channel}</strong>
                  <span style={{ fontSize: 11, color: '#888', marginLeft: 8 }}>{draft.source} · {draft.status}</span>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {draft.status === 'draft' && <button onClick={() => approveDraft(draft.id)} style={primaryBtn}>Approve</button>}
                  <button onClick={() => trySend(draft.id)} style={ghostBtn}>Try send</button>
                </div>
              </div>
              {draft.subject && <div style={{ fontSize: 12, fontWeight: 600 }}>{draft.subject}</div>}
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, color: '#444', margin: 0, fontFamily: 'inherit' }}>{draft.body}</pre>
            </div>
          ))}
        </Card>
      )}

      {tab === 'pay' && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Smartphone size={16} color="#16a34a" />
            <strong>Text-to-pay</strong>
          </div>
          <p style={{ fontSize: 12, color: '#666' }}>
            Empire Workroom uses a non-expiring Stripe Payment Link. Nelma&apos;s uses Square. The message is a draft SMS or WhatsApp.
          </p>
          {!selectedJob && <div style={{ fontSize: 12, color: '#aaa' }}>Select a job first.</div>}
          {selectedJob && (
            <>
              <div style={{ fontSize: 13, marginBottom: 10 }}>{selectedJob.job_number} · {money(selectedJob.quoted_amount)} · {selectedJob.business_unit}</div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                {(['sms', 'whatsapp'] as const).map(ch => (
                  <button key={ch} onClick={() => setPayChannel(ch)} style={{
                    ...ghostBtn, borderColor: payChannel === ch ? '#16a34a' : '#e5e2dc', background: payChannel === ch ? '#f0fdf4' : '#fff',
                  }}>{ch}</button>
                ))}
              </div>
              <button onClick={createPayDraft} style={primaryBtn}><CreditCard size={12} /> Draft {payChannel} with payment link</button>
            </>
          )}
        </Card>
      )}

      {tab === 'costing' && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Scale size={16} color="#b8960c" />
            <strong>Planned vs actual</strong>
          </div>
          {!costing && <div style={{ fontSize: 12, color: '#aaa' }}>Select a job to see costing.</div>}
          {costing && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 12 }}>
                <Kpi label="Revenue" value={money(costing.revenue)} color="#1a1a1a" />
                <Kpi label="Planned margin" value={`${costing.planned.margin_pct}%`} color="#2563eb" />
                <Kpi label="Actual margin" value={`${costing.actual.margin_pct}%`} color="#16a34a" />
              </div>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', marginBottom: 12 }}>
                <thead>
                  <tr style={{ textAlign: 'left', color: '#888' }}>
                    <th style={{ padding: '6px 0' }}></th><th>Planned</th><th>Actual</th><th>Variance</th>
                  </tr>
                </thead>
                <tbody>
                  {['materials', 'labor', 'total'].map(row => (
                    <tr key={row}>
                      <td style={{ padding: '6px 0', textTransform: 'capitalize' }}>{row}</td>
                      <td>{money(costing.planned[row])}</td>
                      <td>{money(costing.actual[row])}</td>
                      <td>{money(costing.variance[row])}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <input value={actualMaterials} onChange={e => setActualMaterials(e.target.value)} placeholder="Actual materials" style={inputStyle} />
                <input value={actualLabor} onChange={e => setActualLabor(e.target.value)} placeholder="Actual labor" style={inputStyle} />
                <button onClick={addActuals} style={primaryBtn}>Record actuals</button>
              </div>
            </>
          )}
        </Card>
      )}

      {tab === 'credits' && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <DollarSign size={16} color="#16a34a" />
            <strong>Credit memos & overpayments</strong>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 8, marginBottom: 12 }}>
            <input value={creditForm.customer_id} onChange={e => setCreditForm({ ...creditForm, customer_id: e.target.value })} placeholder="Customer id" style={inputStyle} />
            <input value={creditForm.amount} onChange={e => setCreditForm({ ...creditForm, amount: e.target.value })} placeholder="Amount" style={inputStyle} />
            <input value={creditForm.reason} onChange={e => setCreditForm({ ...creditForm, reason: e.target.value })} placeholder="Reason" style={inputStyle} />
            <input value={creditForm.invoice_id} onChange={e => setCreditForm({ ...creditForm, invoice_id: e.target.value })} placeholder="Invoice id" style={inputStyle} />
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <button onClick={createMemo} style={primaryBtn}>Post credit memo</button>
            <button onClick={applyCredit} style={ghostBtn}>Apply to invoice</button>
          </div>
          {credits && (
            <div style={{ fontSize: 13 }}>
              <div>Available: <strong>{money(credits.available)}</strong> (credits {money(credits.credit_balance)} · overpayments {money(credits.overpayment_balance)})</div>
              {(credits.memos || []).map((memo: any) => (
                <div key={memo.id} style={{ fontSize: 12, color: '#555', marginTop: 6 }}>
                  {memo.memo_number} · {money(memo.amount)} · {memo.source} · {memo.status}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === 'family' && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <AlertTriangle size={16} color="#7c3aed" />
            <strong>Family request alerts</strong>
          </div>
          <p style={{ fontSize: 12, color: '#666' }}>
            Juan (Max-e) and Camilo (Maxine) submit via Pedir ayuda a Max. Only Rafael is notified. Feature-flagged. No-op without credentials. AMP/Maxine code is not merged into Studio.
          </p>
          {familyStatus && (
            <div style={{ fontSize: 12, color: '#555', marginBottom: 12, display: 'grid', gap: 4 }}>
              <div>Flag: {familyStatus.feature_enabled ? 'on' : 'off'} · Channel: {familyStatus.channel} · Recipient: {familyStatus.recipient_name} ({familyStatus.recipient_role})</div>
              <div>Would deliver: {familyStatus.delivery_would}{familyStatus.noop_reason ? ` — ${familyStatus.noop_reason}` : ''}</div>
              <div>Store: {familyStatus.family_help_db}</div>
            </div>
          )}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <select value={familyForm.requester} onChange={e => setFamilyForm({ ...familyForm, requester: e.target.value })} style={inputStyle}>
              <option value="juan">Juan / Max-e</option>
              <option value="camilo">Camilo / Maxine</option>
            </select>
            <input value={familyForm.message} onChange={e => setFamilyForm({ ...familyForm, message: e.target.value })} style={{ ...inputStyle, minWidth: 320 }} />
            <button onClick={submitFamily} style={primaryBtn}>Submit family help</button>
          </div>
          {alerts.map(alert => (
            <div key={alert.id} style={{ padding: '10px 0', borderBottom: '1px solid #f0ece4', fontSize: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{alert.requester} · {alert.requester_agent}</strong>
                <Pill label={`${alert.classification} · ${alert.delivery_status}`} color="#7c3aed" />
              </div>
              <div style={{ color: '#555', marginTop: 4 }}>{alert.summary}</div>
              <div style={{ color: '#888' }}>Owner only · {alert.recipient_role}{alert.noop_reason ? ` · ${alert.noop_reason}` : ''}</div>
            </div>
          ))}
        </Card>
      )}

      <div style={{ marginTop: 18, fontSize: 11, color: '#999', display: 'flex', alignItems: 'center', gap: 6 }}>
        <CheckCircle2 size={12} /> Isolated Sprint M store · no client_aliases / business.json / .env writes · Studio line only
      </div>
    </div>
  );
}

function Kpi({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ background: '#faf9f6', borderRadius: 10, padding: 10 }}>
      <div style={{ fontSize: 10, color: '#888', fontWeight: 700, textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

const primaryBtn: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 10,
  fontSize: 12, fontWeight: 700, padding: '7px 12px', border: 'none', borderRadius: 8,
  background: '#16a34a', color: '#fff', cursor: 'pointer',
};

const ghostBtn: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6,
  fontSize: 11, fontWeight: 600, padding: '6px 10px', border: '1px solid #e5e2dc',
  borderRadius: 8, background: '#fff', color: '#444', cursor: 'pointer',
};

const inputStyle: React.CSSProperties = {
  fontSize: 12, padding: '7px 10px', border: '1px solid #e5e2dc', borderRadius: 8, background: '#fff',
};
