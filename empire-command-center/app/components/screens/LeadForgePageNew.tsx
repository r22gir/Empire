'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { useTranslation } from '../../lib/i18n';
import {
  Target, Search, Users, Mail, Phone, BarChart3, Calendar,
  Plus, Filter, ChevronRight, Loader2, Send, MessageCircle,
  TrendingUp, AlertTriangle, CheckCircle, Clock, Flame, Snowflake,
  Sun, Eye, Star, ArrowRight, Zap, Globe, MapPin, DollarSign,
  Activity, Crosshair, ArrowLeft
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import WorkroomLeadForm from '../workroom/WorkroomLeadForm';

const LF_API = `${API}/leads`;

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'intake', label: 'Workroom Intake', icon: Mail },
  { id: 'pipeline', label: 'Pipeline', icon: Target },
  { id: 'finder', label: 'Prospect Finder', icon: Crosshair },
  { id: 'campaigns', label: 'Campaigns', icon: Send },
  { id: 'followups', label: 'Follow-ups', icon: Clock },
  { id: 'activity', label: 'Activity Feed', icon: Activity },
  { id: 'reports', label: 'Reports', icon: BarChart3 },
  { id: 'docs', label: 'Docs', icon: BarChart3 },
] as const;

type Section = typeof NAV[number]['id'];

const TEMP_ICONS: Record<string, React.ReactNode> = {
  hot: <Flame size={12} style={{ color: '#dc2626' }} />,
  warm: <Sun size={12} style={{ color: '#eab308' }} />,
  cold: <Snowflake size={12} style={{ color: '#3b82f6' }} />,
};

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  new: { bg: '#dbeafe', text: '#2563eb' },
  contacted: { bg: '#fef3c7', text: '#d97706' },
  responded: { bg: '#d1fae5', text: '#059669' },
  qualified: { bg: '#ede9fe', text: '#7c3aed' },
  proposal_sent: { bg: '#fce7f3', text: '#db2777' },
  negotiating: { bg: '#fdf8eb', text: '#b8960c' },
  won: { bg: '#dcfce7', text: '#16a34a' },
  lost: { bg: '#fef2f2', text: '#dc2626' },
  nurture: { bg: '#f5f3ef', text: '#888' },
};

interface LeadForgePageProps { initialSection?: string; }

export default function LeadForgePage({ initialSection }: LeadForgePageProps) {
  const [section, setSection] = useState<Section>((initialSection as Section) || 'dashboard');
  const { t } = useTranslation('leads');

  useEffect(() => { if (initialSection) setSection(initialSection as Section); }, [initialSection]);
  useEffect(() => {
    const el = document.querySelector(`[data-lf-tab="${section}"]`) as HTMLElement | null;
    const nav = el?.parentElement;
    if (el && nav && nav.scrollWidth > nav.clientWidth) nav.scrollTo({ left: el.offsetLeft - 12, behavior: 'smooth' });
  }, [section]);

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection />;
      case 'intake': return <WorkroomIntakeSection />;
      case 'pipeline': return <PipelineSection />;
      case 'finder': return <ProspectFinderSection />;
      case 'campaigns': return <CampaignsSection />;
      case 'followups': return <FollowupsSection />;
      case 'activity': return <ActivitySection />;
      case 'reports': return <ReportsSection />;
      case 'docs': return <ProductDocs product="leadforge" />;
      default: return <DashboardSection />;
    }
  };

  return (
    <div className="cy-module" style={{ display: 'flex', height: '100%', background: '#faf9f7' }}>
      <div className="cy-module-nav" style={{ width: 200, borderRight: '1px solid #e5e2dc', padding: '16px 0', flexShrink: 0, overflowY: 'auto' }}>
        <div style={{ padding: '0 16px 12px', borderBottom: '1px solid #e5e2dc', marginBottom: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#dc2626', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Crosshair size={16} /> LeadForge
          </div>
          <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>AI-Powered Client Acquisition</div>
        </div>
        {NAV.map(n => (
          <button key={n.id} data-lf-tab={n.id} onClick={() => setSection(n.id)} style={{
            display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '8px 16px',
            border: 'none', cursor: 'pointer', background: section === n.id ? '#fef2f2' : 'transparent',
            color: section === n.id ? '#dc2626' : '#666', fontWeight: section === n.id ? 600 : 400,
            fontSize: 12, textAlign: 'left',
          }}>
            <n.icon size={14} /> {n.label}
          </button>
        ))}
      </div>
      <div className="cy-module-main" style={{ flex: 1, minWidth: 0, overflowY: 'auto', overflowX: 'hidden', padding: '20px 24px' }}>{renderContent()}</div>
    </div>
  );
}

function SH({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>{title}</h2>
        {subtitle && <p style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

function Kpi({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '16px 18px', flex: 1, minWidth: 130 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#888', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || '#1a1a1a', marginTop: 4 }}>{value}</div>
    </div>
  );
}

function DashboardSection() {
  const [leads, setLeads] = useState<any[]>([]);
  useEffect(() => { fetch(`${LF_API}`).then(r => r.json()).then(d => setLeads(d.leads || d || [])).catch(() => {}); }, []);
  const hot = leads.filter((l: any) => l.temperature === 'hot').length;
  const pipeline = leads.filter((l: any) => !['won', 'lost'].includes(l.status)).reduce((s: number, l: any) => s + (l.estimated_value || 0), 0);
  const won = leads.filter((l: any) => l.status === 'won');
  const winRate = leads.length > 0 ? Math.round(won.length / leads.length * 100) : 0;

  return (
    <div>
      <SH title="LeadForge Dashboard" subtitle="Your AI-powered sales command center" />
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <Kpi label="Hot Leads" value={hot} color="#dc2626" />
        <Kpi label="Pipeline Value" value={`$${pipeline.toLocaleString()}`} color="#b8960c" />
        <Kpi label="Win Rate" value={`${winRate}%`} color="#16a34a" />
        <Kpi label="Total Leads" value={leads.length} color="#2563eb" />
      </div>
      {/* AI Recommendation Banner */}
      <div style={{ background: 'linear-gradient(135deg, #fdf8eb, #fff7ed)', border: '1px solid #f5d89a', borderRadius: 10, padding: 14, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
        <Zap size={18} style={{ color: '#b8960c' }} />
        <div style={{ fontSize: 12 }}>
          <span style={{ fontWeight: 600, color: '#b8960c' }}>MAX AI:</span>{' '}
          <span style={{ color: '#666' }}>Click "Prospect Finder" to discover potential clients in your area using AI-powered web search.</span>
        </div>
      </div>
      {/* Recent activity */}
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Today's Actions</h3>
        {leads.length === 0 ? (
          <div style={{ fontSize: 12, color: '#999', padding: 16, textAlign: 'center' }}>No leads yet. Use Prospect Finder to start discovering clients.</div>
        ) : (
          <div style={{ fontSize: 12 }}>
            {leads.filter((l: any) => l.status === 'new').length > 0 && (
              <div style={{ padding: '6px 0', borderBottom: '1px solid #f0ede6' }}>
                <AlertTriangle size={12} style={{ color: '#eab308', verticalAlign: 'text-bottom' }} /> {leads.filter((l: any) => l.status === 'new').length} new leads need first contact
              </div>
            )}
            {leads.filter((l: any) => l.temperature === 'hot').length > 0 && (
              <div style={{ padding: '6px 0' }}>
                <Flame size={12} style={{ color: '#dc2626', verticalAlign: 'text-bottom' }} /> {hot} hot leads — follow up immediately
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function WorkroomIntakeSection() {
  return (
    <div style={{ maxWidth: 560 }}>
      <SH
        title="Workroom intake"
        subtitle="business=workroom. Saves a LeadForge lead and a ForgeCRM contact. LuxeForge posts to the same API."
      />
      <WorkroomLeadForm captureSurface="command_center" showOperatorResult />
    </div>
  );
}

function PipelineSection() {
  const [leads, setLeads] = useState<any[]>([]);
  const [quoteState, setQuoteState] = useState<Record<number, string>>({});
  const [busyId, setBusyId] = useState<number | null>(null);
  useEffect(() => { fetch(`${LF_API}?limit=500`).then(r => r.json()).then(d => setLeads(d.leads || d || [])).catch(() => setLeads([])); }, []);

  const createQuote = async (leadId: number) => {
    setBusyId(leadId);
    try {
      const res = await fetch(`${LF_API}/${leadId}/workroom-quote`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Quote failed');
      const quote = data.quote || {};
      setQuoteState(prev => ({ ...prev, [leadId]: quote.quote_number || quote.id || 'saved' }));
    } catch {
      setQuoteState(prev => ({ ...prev, [leadId]: 'failed' }));
    } finally {
      setBusyId(null);
    }
  };

  const COLS = [
    { key: 'new', label: 'New' },
    { key: 'contacted', label: 'Contacted' },
    { key: 'responded', label: 'Responded' },
    { key: 'qualified', label: 'Qualified' },
    { key: 'proposal_sent', label: 'Proposal' },
    { key: 'negotiating', label: 'Negotiating' },
    { key: 'won', label: 'Won' },
  ];

  return (
    <div>
      <SH title="Sales Pipeline" subtitle="Drag leads through your sales funnel"
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> Add Lead</button>} />
      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 12 }}>
        {COLS.map(col => {
          const cards = Array.isArray(leads) ? leads.filter((l: any) => l.status === col.key) : (leads as any)[col.key] || [];
          const totalValue = cards.reduce((s: number, l: any) => s + (l.estimated_value || 0), 0);
          return (
            <div key={col.key} style={{ minWidth: 180, background: '#f5f3ef', borderRadius: 10, padding: 10, flex: 1 }}>
              <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: STATUS_COLORS[col.key]?.text || '#666' }}>{col.label}</span>
                <span style={{ color: '#999' }}>{cards.length}</span>
              </div>
              {totalValue > 0 && <div style={{ fontSize: 9, color: '#b8960c', fontWeight: 600, marginBottom: 6 }}>${totalValue.toLocaleString()}</div>}
              {cards.length === 0 ? <div style={{ fontSize: 10, color: '#ccc', textAlign: 'center', padding: 12 }}>—</div> : cards.map((lead: any) => (
                <div key={lead.id} style={{ background: '#fff', borderRadius: 8, padding: 10, marginBottom: 6, border: '1px solid #e5e2dc', fontSize: 11, cursor: 'pointer' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600 }}>{[lead.first_name, lead.last_name].filter(Boolean).join(' ') || lead.company || `Lead #${lead.id}`}</span>
                    {TEMP_ICONS[lead.temperature]}
                  </div>
                  {lead.company && (lead.first_name || lead.last_name) && <div style={{ color: '#888', fontSize: 10 }}>{lead.company}</div>}
                  {lead.next_action_date && <div style={{ fontSize: 9, color: lead.next_action_date.slice(0, 10) <= new Date().toISOString().slice(0, 10) ? '#dc2626' : '#2563eb', fontWeight: 600, marginTop: 2 }}>⏰ {lead.next_action_date.slice(0, 10)} · {lead.next_action || 'Follow up'}</div>}
                  {lead.estimated_value > 0 && <div style={{ color: '#b8960c', fontWeight: 600, fontSize: 10 }}>${lead.estimated_value.toLocaleString()}</div>}
                  <div style={{ fontSize: 10, color: '#666', marginTop: 2 }}>
                    Source: {lead.source || '—'}{lead.utm_campaign ? ` · ${lead.utm_campaign}` : ''}
                  </div>
                  {lead.business_unit === 'workroom' && (
                    quoteState[lead.id] && quoteState[lead.id] !== 'failed' ? (
                      <div style={{ fontSize: 9, color: '#16a34a', fontWeight: 600, marginTop: 4 }}>Quote {quoteState[lead.id]}</div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => createQuote(lead.id)}
                        disabled={busyId === lead.id}
                        style={{ marginTop: 6, fontSize: 9, padding: '3px 6px', background: '#1a1a2e', color: '#d4af37', border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 700 }}
                      >
                        {busyId === lead.id ? 'Opening…' : quoteState[lead.id] === 'failed' ? 'Retry quote' : 'Create Workroom quote'}
                      </button>
                    )
                  )}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function useIsMobile(bp = 767) {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${bp}px)`);
    const update = () => setMobile(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, [bp]);
  return mobile;
}

const pName = (p: any) => p?.display_name || p?.name || p?.business_name || '—';
const pCity = (p: any) => p?.display_city || p?.location || p?.city || '';
const scoreColor = (s: number) => (s >= 60 ? '#16a34a' : s >= 30 ? '#b8960c' : '#999');
const FIT_KEYS = ['designer', 'window_treatments', 'upholstery', 'millwork', 'cabinetry', 'hospitality', 'restaurant', 'gc'];

const ENRICH_STATUS: Record<string, string> = {
  found: 'Found on their website',
  nothing_found: 'Website checked: no owner name or email published',
  no_website: 'No website on file yet',
  skipped_directory: 'Listing is a directory page (Yelp, Houzz...), not their own site',
  blocked_by_robots: "Their robots.txt asks bots not to read these pages, so we didn't",
  unreachable: 'Website did not respond',
};

function TypeTag({ p }: { p: any }) {
  if (p?.is_directory_page) return <span className="lf-tag" style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#f5f3ef', color: '#888', fontWeight: 600 }}>directory page</span>;
  if (!p?.client_type) return null;
  return <span className="lf-tag" style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#fdf8eb', color: '#b8960c', fontWeight: 600, textTransform: 'capitalize' }}>{p.client_type}</span>;
}

function ScorePill({ score, big }: { score: number; big?: boolean }) {
  return (
    <span style={{ flexShrink: 0, minWidth: big ? 58 : 36, textAlign: 'center', fontWeight: 700, fontSize: big ? 14 : 13, padding: big ? '4px 10px' : '3px 8px', borderRadius: 999, border: `1px solid ${scoreColor(score)}`, color: scoreColor(score) }}>
      {score}{big ? '/100' : ''}
    </span>
  );
}

function InfoRow({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '7px 0', borderBottom: '1px solid #f0ede6', fontSize: 13, minWidth: 0 }}>
      <span style={{ color: '#888', flexShrink: 0, marginTop: 2 }}>{icon}</span>
      <span style={{ color: '#888', width: 78, flexShrink: 0 }}>{label}</span>
      <span style={{ flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>{children}</span>
    </div>
  );
}

function ProspectDetail({ p, pipe, onPipeline, onEnriched }: {
  p: any; pipe?: { status?: string; lead_id?: number };
  onPipeline: (id: number) => Promise<any>; onEnriched: (updated: any) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [draft, setDraft] = useState<any>(null);
  const [crm, setCrm] = useState<string | null>(null);
  useEffect(() => { setNote(null); setDraft(null); setCrm(null); }, [p?.id]);

  const inPipeline = pipe?.status === 'added' || pipe?.status === 'already_in_pipeline';
  const contactName = p.contact_name;
  const email = p.contact_email || p.email;
  const hasContact = Boolean(contactName || email || p.instagram || p.contact_phone);
  const fits = FIT_KEYS.filter(k => p[`${k}_fit`]).map(k => k.replace('_', ' '));

  const findContact = async () => {
    setBusy('enrich'); setNote(null);
    try {
      const res = await fetch(`${LF_API}/leadforge/prospects/${p.id}/enrich?force=true`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Lookup failed');
      if (data.prospect) onEnriched(data.prospect);
      const r = (data.results || [])[0] || {};
      setNote(ENRICH_STATUS[r.status] || r.status || 'Done');
    } catch (e: any) { setNote(e.message || 'Lookup failed'); }
    setBusy(null);
  };
  const addPipe = async () => { setBusy('pipe'); await onPipeline(p.id); setBusy(null); };
  const toCrm = async () => {
    setBusy('crm');
    try {
      const pipeRes = pipe?.lead_id ? { lead_id: pipe.lead_id } : await onPipeline(p.id);
      const leadId = pipeRes?.lead_id;
      if (!leadId) throw new Error('No lead');
      const res = await fetch(`${LF_API}/${leadId}/promote`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'CRM failed');
      setCrm(data.promote_outcome === 'already_promoted' ? 'Already in ForgeCRM' : 'Added to ForgeCRM');
    } catch (e: any) { setCrm(e.message || 'CRM failed'); }
    setBusy(null);
  };
  const makeDraft = async (channel: string) => {
    setBusy(channel);
    try {
      const res = await fetch(`${LF_API}/leadforge/prospects/${p.id}/drafts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ channel }),
      });
      setDraft(await res.json());
    } catch { setDraft({ body: 'Draft failed' }); }
    setBusy(null);
  };

  const btn = (bg: string): React.CSSProperties => ({ fontSize: 13, padding: '9px 12px', background: bg, color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 5 });

  return (
    <div className="lf-detail" style={{ minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 6 }}>
        <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0, flex: 1, minWidth: 0, overflowWrap: 'anywhere', lineHeight: 1.25 }}>{pName(p)}</h3>
        <ScorePill score={p.score || 0} big />
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', fontSize: 12, color: '#666', marginBottom: 14 }}>
        {pCity(p) && <span><MapPin size={11} style={{ verticalAlign: 'text-bottom' }} /> {pCity(p)}</span>}
        <TypeTag p={p} />
        {inPipeline && <span style={{ color: '#16a34a', fontWeight: 600 }}>✓ In pipeline{pipe?.lead_id ? ` · Lead #${pipe.lead_id}` : ''}</span>}
      </div>

      {/* Who is this business */}
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '6px 12px', marginBottom: 12 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#888', textTransform: 'uppercase', padding: '6px 0 2px' }}>Who is this</div>
        <InfoRow icon={<Star size={13} />} label="Category">{p.category || p.client_type || '—'}</InfoRow>
        <InfoRow icon={<Globe size={13} />} label="Website">
          {p.website && !p.is_directory_page
            ? <a href={p.website} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb' }}>{String(p.website).replace(/https?:\/\/(www\.)?/, '').replace(/\/$/, '').slice(0, 48)}</a>
            : p.website ? <a href={p.website} target="_blank" rel="noopener noreferrer" style={{ color: '#888' }}>directory listing</a> : <span style={{ color: '#999' }}>unknown</span>}
        </InfoRow>
        <InfoRow icon={<Phone size={13} />} label="Phone">
          {p.phone ? <a href={`tel:${p.phone}`} style={{ color: '#2563eb' }}>{p.phone}</a> : <span style={{ color: '#999' }}>unknown</span>}
        </InfoRow>
        <InfoRow icon={<MapPin size={13} />} label="Maps">
          {p.maps_url ? <a href={p.maps_url} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb' }}>Open in Google Maps</a> : '—'}
          {p.address && <div style={{ color: '#666', fontSize: 12, marginTop: 2 }}>{p.address}</div>}
        </InfoRow>
        {(p.rating || p.review_count) ? (
          <InfoRow icon={<Star size={13} />} label="Reviews">{p.rating ? `${p.rating}★` : ''} {p.review_count ? `(${p.review_count})` : ''}</InfoRow>
        ) : null}
      </div>

      {/* Contact */}
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '6px 12px 10px', marginBottom: 12 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#888', textTransform: 'uppercase', padding: '6px 0 2px' }}>Contact</div>
        {hasContact ? (
          <>
            {contactName && <InfoRow icon={<Users size={13} />} label="Name">{contactName}{p.contact_title ? <span style={{ color: '#888' }}> · {p.contact_title}</span> : null}</InfoRow>}
            {email && <InfoRow icon={<Mail size={13} />} label="Email"><a href={`mailto:${email}`} style={{ color: '#2563eb' }}>{email}</a></InfoRow>}
            {p.contact_phone && p.contact_phone !== p.phone && <InfoRow icon={<Phone size={13} />} label="Direct"><a href={`tel:${p.contact_phone}`} style={{ color: '#2563eb' }}>{p.contact_phone}</a></InfoRow>}
            {p.instagram && <InfoRow icon={<MessageCircle size={13} />} label="Instagram"><a href={p.instagram} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb' }}>@{String(p.instagram).replace(/\/$/, '').split('/').pop()}</a></InfoRow>}
            {p.facebook && <InfoRow icon={<Globe size={13} />} label="Facebook"><a href={p.facebook} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb' }}>Page</a></InfoRow>}
            {p.linkedin && <InfoRow icon={<Globe size={13} />} label="LinkedIn"><a href={p.linkedin} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb' }}>Profile</a></InfoRow>}
            {!contactName && <div style={{ fontSize: 12, color: '#888', marginTop: 6 }}>Owner / principal name: unknown</div>}
          </>
        ) : (
          <div style={{ fontSize: 13, padding: '6px 0' }}>
            <div style={{ fontWeight: 600 }}>Contact: unknown</div>
            <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
              {p.enrichment_status ? (ENRICH_STATUS[p.enrichment_status] || p.enrichment_status) : 'No owner name or email yet. The free lookup reads their own website (home, contact, about, team pages) and respects robots.txt.'}
            </div>
          </div>
        )}
        <button onClick={findContact} disabled={busy === 'enrich'} style={{ ...btn('#d4af37'), marginTop: 8, color: '#1a1a2e' }}>
          {busy === 'enrich' ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
          {busy === 'enrich' ? 'Checking website…' : hasContact ? 'Refresh contact (free)' : 'Find contact (free lookup)'}
        </button>
        {note && <div style={{ fontSize: 12, color: '#666', marginTop: 6 }}>{note}</div>}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        {inPipeline
          ? <span style={{ ...btn('#16a34a'), cursor: 'default' }}><CheckCircle size={13} /> In pipeline</span>
          : <button onClick={addPipe} disabled={busy === 'pipe'} style={btn('#dc2626')}><Plus size={13} /> {busy === 'pipe' ? 'Adding…' : 'Pipeline'}</button>}
        <button onClick={toCrm} disabled={busy === 'crm'} style={btn('#7c3aed')}><ArrowRight size={13} /> {busy === 'crm' ? 'Saving…' : 'ForgeCRM'}</button>
        {p.phone && <a href={`tel:${p.phone}`} style={btn('#16a34a')}><Phone size={13} /> Call</a>}
        {p.website && !p.is_directory_page && <a href={p.website} target="_blank" rel="noopener noreferrer" style={btn('#2563eb')}><Globe size={13} /> Website</a>}
      </div>
      {crm && <div style={{ fontSize: 12, color: '#7c3aed', marginBottom: 10 }}>{crm}</div>}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        <button onClick={() => makeDraft('email')} disabled={!!busy} style={{ ...btn('#f5f3ef'), color: '#444', border: '1px solid #e5e2dc' }}><Mail size={13} /> Draft email</button>
        <button onClick={() => makeDraft('instagram_dm')} disabled={!!busy} style={{ ...btn('#f5f3ef'), color: '#444', border: '1px solid #e5e2dc' }}><MessageCircle size={13} /> Draft IG DM</button>
      </div>
      {draft && (
        <div style={{ background: '#faf9f7', border: '1px solid #e5e2dc', borderRadius: 8, padding: 10, marginBottom: 12, fontSize: 12 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', marginBottom: 4 }}>DRAFT ONLY — NOTHING SENT{draft.to_address ? ` · to ${draft.to_address}` : ' · no address yet'}</div>
          {draft.subject && <div style={{ fontWeight: 600, marginBottom: 4 }}>{draft.subject}</div>}
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{draft.body}</div>
          <button onClick={() => navigator.clipboard?.writeText(draft.body || '')} style={{ marginTop: 6, fontSize: 11, padding: '4px 10px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 6, cursor: 'pointer' }}>Copy</button>
        </div>
      )}

      {fits.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 10 }}>
          {fits.map(t => <span key={t} style={{ fontSize: 10, padding: '2px 7px', borderRadius: 4, background: '#fdf8eb', color: '#b8960c', fontWeight: 600 }}>{t}</span>)}
        </div>
      )}
      {p.recommended_angle && <div style={{ fontSize: 12, color: '#555', marginBottom: 8, fontStyle: 'italic' }}>Angle: {p.recommended_angle}</div>}
      <details style={{ background: '#faf9f7', borderRadius: 8, padding: '8px 10px', fontSize: 12 }}>
        <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Score {p.score || 0}/100 · confidence {p.confidence_score || 0}%</summary>
        <div style={{ marginTop: 6, lineHeight: 1.6 }}>
          <div>Rating: {p.rating_points || 0}/40 {p.rating ? `(${p.rating}★)` : ''}</div>
          <div>Reviews: {p.review_points || 0}/30 {p.review_count ? `(${p.review_count})` : ''}</div>
          <div>Relevance: {p.relevance_points || 0}/20</div>
          <div>Proximity: {p.proximity_points || 0}/10</div>
          <div>Keywords: {p.keyword_bonus || 0}/10</div>
          <div>Source: {p.source_bonus || 0}/5 ({p.source})</div>
        </div>
      </details>
    </div>
  );
}

function ProspectFinderSection() {
  const isMobile = useIsMobile();
  const [bizUnit, setBizUnit] = useState('workroom');
  const [location, setLocation] = useState('DMV');
  const [target, setTarget] = useState('interior designers');
  const [searching, setSearching] = useState(false);
  const [prospects, setProspects] = useState<any[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [searchMeta, setSearchMeta] = useState<any>(null);
  const [pipeline, setPipeline] = useState<Record<number, { status?: string; lead_id?: number }>>({});
  const [selected, setSelected] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  const loadList = async () => {
    const listRes = await fetch(`${LF_API}/leadforge/prospects?limit=500`);
    const listData = await listRes.json();
    setProspects(listData.prospects || listData || []);
    fetch(`${LF_API}/leadforge/prospects/stats`).then(r => r.json()).then(s => setTotal(s.total_prospects ?? null)).catch(() => {});
  };

  useEffect(() => {
    Promise.all([
      loadList(),
      fetch(`${LF_API}/leadforge/prospect-pipeline?limit=1000`).then(r => r.json()).catch(() => []),
    ]).then(([, pipelineData]) => {
      const pipeItems = (pipelineData as any)?.pipeline || pipelineData || [];
      const status: Record<number, { status?: string }> = {};
      for (const pp of pipeItems) if (pp.prospect_id) status[pp.prospect_id] = { status: 'already_in_pipeline' };
      setPipeline(status);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  // Phone: the detail is a full-screen sheet; the hardware/browser back button closes it.
  useEffect(() => {
    if (!isMobile || !selected) return;
    window.history.pushState({ lfSheet: true }, '');
    const onPop = () => setSelected(null);
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, [isMobile, selected?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const closeSheet = () => {
    if (isMobile && window.history.state?.lfSheet) window.history.back();
    else setSelected(null);
  };

  const findProspects = async () => {
    setSearching(true);
    try {
      const res = await fetch(`${LF_API}/leadforge/prospects/search`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_unit: bizUnit, location, target_type: target }),
      });
      setSearchMeta(await res.json());
      await loadList();
    } catch { /* keep existing */ }
    setSearching(false);
  };

  const addToPipeline = async (prospectId: number) => {
    try {
      const res = await fetch(`${LF_API}/leadforge/prospects/${prospectId}/pipeline?assigned_unit=${encodeURIComponent(bizUnit)}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) return null;
      setPipeline(prev => ({ ...prev, [prospectId]: { status: data.status, lead_id: data.lead_id } }));
      return data;
    } catch { return null; }
  };

  const onEnriched = (updated: any) => {
    setProspects(prev => prev.map(x => (x.id === updated.id ? { ...x, ...updated } : x)));
    setSelected((cur: any) => (cur?.id === updated.id ? { ...cur, ...updated } : cur));
  };

  const q = filter.trim().toLowerCase();
  const shown = q ? prospects.filter(p => `${pName(p)} ${pCity(p)} ${p.client_type || ''} ${p.category || ''}`.toLowerCase().includes(q)) : prospects;
  const inPipe = (id: number) => ['added', 'already_in_pipeline'].includes(pipeline[id]?.status || '');

  return (
    <div className="lf-finder" style={{ minWidth: 0, maxWidth: '100%' }}>
      <SH title="Prospect Finder" subtitle={`${total ?? prospects.length} prospects in database`} />
      <div style={{ background: 'linear-gradient(135deg, #fef2f2, #fff)', border: '1px solid #fca5a5', borderRadius: 10, padding: isMobile ? 12 : 16, marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#dc2626', marginBottom: 10 }}>
          <Crosshair size={14} style={{ verticalAlign: 'text-bottom' }} /> THE WEAPON — Real Prospect Discovery (Brave + Google + Yelp)
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
          <div style={{ flex: 1, minWidth: 140 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Business Unit</label>
            <select value={bizUnit} onChange={e => setBizUnit(e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12 }}>
              <option value="workroom">Empire Workroom (Drapery)</option>
              <option value="woodcraft">WoodCraft (Custom Woodwork)</option>
              <option value="empire_saas">Empire Box (SaaS)</option>
            </select>
          </div>
          <div style={{ flex: 1, minWidth: 140 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Location</label>
            <input value={location} onChange={e => setLocation(e.target.value)} placeholder="DMV, Washington DC, nationwide..."
              style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12 }} />
          </div>
          <div style={{ flex: 1, minWidth: 140 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Target Type</label>
            <input value={target} onChange={e => setTarget(e.target.value)} placeholder="interior designers, contractors..."
              style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12 }} />
          </div>
        </div>
        <button onClick={findProspects} disabled={searching} style={{
          padding: '10px 20px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 8,
          fontWeight: 700, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {searching ? <Loader2 size={14} className="animate-spin" /> : <Crosshair size={14} />}
          {searching ? 'Searching...' : 'Find Prospects'}
        </button>
        {searchMeta && (
          <div style={{ marginTop: 8, fontSize: 11, color: '#888', overflowWrap: 'anywhere' }}>
            {searchMeta.success === false
              ? `Search failed: ${searchMeta.error || 'unknown error'}`
              : <>Last search: {searchMeta.raw_result_count || 0} raw → {searchMeta.unique_result_count || 0} unique → {searchMeta.inserted_count || 0} new |
                Providers: {(searchMeta.providers_succeeded || []).join(', ') || 'none'}
                {(searchMeta.providers_failed || []).length > 0 && ` | failed: ${(searchMeta.providers_failed || []).map((f: any) => f.provider).join(', ')}`}</>}
          </div>
        )}
      </div>

      {loading && <div style={{ textAlign: 'center', padding: 30, color: '#999' }}>Loading prospects...</div>}
      {!loading && prospects.length === 0 && <div style={{ textAlign: 'center', padding: 30, color: '#999' }}>No prospects yet — run a search above</div>}

      {prospects.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, margin: 0, flex: '1 1 auto' }}>{shown.length} Prospects</h3>
          <div style={{ position: 'relative', flex: isMobile ? '1 1 100%' : '0 1 260px' }}>
            <Search size={13} style={{ position: 'absolute', left: 9, top: 10, color: '#999' }} />
            <input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Filter by name, city, type"
              style={{ width: '100%', padding: '8px 8px 8px 28px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
          </div>
        </div>
      )}

      {/* Phone: full-width tappable list; detail opens as a full-screen sheet */}
      {prospects.length > 0 && isMobile && (
        <div className="lf-plist" role="list">
          {shown.map((p: any) => (
            <button key={p.id} role="listitem" onClick={() => setSelected(p)} className="lf-prow" style={{
              display: 'flex', alignItems: 'center', gap: 10, width: '100%', textAlign: 'left', padding: '12px',
              background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, marginBottom: 8, cursor: 'pointer', color: 'inherit',
            }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 14, lineHeight: 1.3, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', overflowWrap: 'anywhere' }}>{pName(p)}</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', fontSize: 12, color: '#666', marginTop: 4 }}>
                  {pCity(p) && <span><MapPin size={11} style={{ verticalAlign: 'text-bottom' }} /> {pCity(p)}</span>}
                  <TypeTag p={p} />
                  {p.has_contact && <span style={{ color: '#2563eb', fontWeight: 600 }}>contact</span>}
                  {inPipe(p.id) && <span style={{ color: '#16a34a', fontWeight: 600 }}>✓ pipeline</span>}
                </div>
              </div>
              <ScorePill score={p.score || 0} />
              <ChevronRight size={16} style={{ color: '#bbb', flexShrink: 0 }} />
            </button>
          ))}
        </div>
      )}
      {isMobile && selected && (
        <div className="lf-sheet" role="dialog" aria-modal="true" aria-label={pName(selected)} style={{
          position: 'fixed', inset: 0, zIndex: 10050, background: '#faf9f7', overflowY: 'auto', overflowX: 'hidden',
          WebkitOverflowScrolling: 'touch', paddingBottom: 'calc(24px + env(safe-area-inset-bottom))',
        }}>
          {/* Themes turn light inline backgrounds into 88% glass; a full-screen sheet must be opaque. */}
          <style>{`
            html body .cy-shell .lf-sheet.lf-sheet.lf-sheet, html body .cy-shell .lf-sheet .lf-sheet-bar.lf-sheet-bar { background: #061824 !important; }
            html[data-theme="gold"] body .cy-shell .lf-sheet.lf-sheet.lf-sheet, html[data-theme="gold"] body .cy-shell .lf-sheet .lf-sheet-bar.lf-sheet-bar { background: #fbf8f1 !important; }
          `}</style>
          <div className="lf-sheet-bar" style={{ position: 'sticky', top: 0, zIndex: 1, display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', paddingTop: 'calc(10px + env(safe-area-inset-top))', background: '#fff', borderBottom: '1px solid #e5e2dc' }}>
            <button onClick={closeSheet} aria-label="Back to prospects" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 14, fontWeight: 600, padding: '8px 10px', background: 'transparent', border: '1px solid #e5e2dc', borderRadius: 8, cursor: 'pointer', color: 'inherit' }}>
              <ArrowLeft size={16} /> Prospects
            </button>
            <span style={{ flex: 1, minWidth: 0, fontSize: 13, color: '#888', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{pName(selected)}</span>
          </div>
          <div style={{ padding: 14 }}>
            <ProspectDetail p={selected} pipe={pipeline[selected.id]} onPipeline={addToPipeline} onEnriched={onEnriched} />
          </div>
        </div>
      )}

      {/* Desktop: table + side detail (split view) */}
      {prospects.length > 0 && !isMobile && (
        <div style={{ display: 'flex', gap: 16, minWidth: 0 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
                  <th style={{ padding: 6 }}>Name</th>
                  <th style={{ padding: 6 }}>City</th>
                  <th style={{ padding: 6 }}>Type</th>
                  <th style={{ padding: 6 }}>Source</th>
                  <th style={{ padding: 6 }}>Score</th>
                  <th style={{ padding: 6 }}>Contact</th>
                  <th style={{ padding: 6 }}>Action</th>
                </tr></thead>
                <tbody>{shown.map((p: any) => {
                  const srcColor = p.source === 'google_places' ? { bg: '#dbeafe', color: '#2563eb' } :
                                   p.source === 'brave' ? { bg: '#fed7aa', color: '#c2410c' } :
                                   p.source === 'yelp' ? { bg: '#fecaca', color: '#dc2626' } : { bg: '#f0fdf4', color: '#16a34a' };
                  return (
                    <tr key={p.id} onClick={() => setSelected(p)}
                      style={{ borderBottom: '1px solid #f0ede6', cursor: 'pointer', background: selected?.id === p.id ? '#fdf8eb' : '' }}>
                      <td style={{ padding: 6, maxWidth: 280 }}>
                        <div style={{ fontWeight: 500, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={pName(p)}>{pName(p)}</div>
                        {p.phone && <div style={{ fontSize: 9, color: '#666' }}>{p.phone}</div>}
                      </td>
                      <td style={{ padding: 6, color: '#666', fontSize: 10, whiteSpace: 'nowrap' }}>{pCity(p) || '—'}</td>
                      <td style={{ padding: 6 }}><TypeTag p={p} /></td>
                      <td style={{ padding: 6 }}><span style={{ fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 4, background: srcColor.bg, color: srcColor.color }}>{p.platform || p.source}</span></td>
                      <td style={{ padding: 6 }}><span style={{ fontWeight: 700, color: scoreColor(p.score || 0) }}>{p.score || 0}</span></td>
                      <td style={{ padding: 6, fontSize: 10, color: p.has_contact ? '#2563eb' : '#bbb' }}>{p.contact_name || (p.contact_email || p.email ? 'email' : p.instagram ? 'Instagram' : 'unknown')}</td>
                      <td style={{ padding: 6 }} onClick={e => e.stopPropagation()}>
                        {inPipe(p.id) ? (
                          <span style={{ fontSize: 9, color: '#16a34a', fontWeight: 600 }}>✓ Pipeline</span>
                        ) : (
                          <button onClick={() => addToPipeline(p.id)} style={{ fontSize: 9, padding: '2px 6px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}>+ Pipeline</button>
                        )}
                      </td>
                    </tr>
                  );
                })}</tbody>
              </table>
            </div>
          </div>
          {selected && (
            <div style={{ width: 360, background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, flexShrink: 0, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)', position: 'sticky', top: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 4 }}>
                <button onClick={() => setSelected(null)} aria-label="Close" style={{ background: '#f5f3ef', border: 'none', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 11 }}>✕</button>
              </div>
              <ProspectDetail p={selected} pipe={pipeline[selected.id]} onPipeline={addToPipeline} onEnriched={onEnriched} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DraftReviewPanel({ campaignId }: { campaignId: number }) {
  const [drafts, setDrafts] = useState<any[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<any>(null);
  const [sending, setSending] = useState<number | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editSubject, setEditSubject] = useState('');
  const [editBody, setEditBody] = useState('');

  const canSendDraft = (draft: any) => Boolean(draft?.to_email && ['edited', 'reviewed'].includes(draft?.status));
  const sendableDrafts = drafts.filter(canSendDraft);

  useEffect(() => {
    fetch(`${LF_API}/leadforge/campaigns/drafts?campaign_id=${campaignId}`)
      .then(r => r.json()).then(d => setDrafts(d.drafts || d || [])).catch(() => {});
  }, [campaignId]);

  const sendDraft = async (draftId: number) => {
    const draft = drafts.find(d => d.id === draftId);
    if (!canSendDraft(draft)) {
      alert('Review or edit this draft before sending.');
      return;
    }
    setSending(draftId);
    try {
      const res = await fetch(`${LF_API}/leadforge/campaigns/drafts/${draftId}/send`, { method: 'POST' });
      const data = await res.json();
      if (data.success || data.status === 'sent') {
        setDrafts(prev => prev.map(d => d.id === draftId ? { ...d, status: 'sent' } : d));
        setSelectedDraft(null);
      } else {
        alert(`Send failed: ${data.error || 'Unknown error'}`);
      }
    } catch { alert('Send failed'); }
    setSending(null);
  };

  const saveDraftEdit = async () => {
    if (!selectedDraft) return;
    await fetch(`${LF_API}/leadforge/campaigns/drafts/${selectedDraft.id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject: editSubject, body: editBody }),
    });
    setDrafts(prev => prev.map(d => d.id === selectedDraft.id ? { ...d, subject: editSubject, body: editBody, status: 'edited' } : d));
    setEditMode(false);
    setSelectedDraft({ ...selectedDraft, subject: editSubject, body: editBody, status: 'edited' });
  };

  const sendAllReviewed = async () => {
    if (sendableDrafts.length === 0) {
      alert('No reviewed or edited drafts are ready to send.');
      return;
    }
    const res = await fetch(`${LF_API}/leadforge/campaigns/${campaignId}/send-reviewed`, { method: 'POST' });
    const data = await res.json();
    alert(`Sent: ${data.sent || 0}, Failed: ${data.failed || 0}, Skipped: ${data.skipped || 0}`);
    // Refresh
    fetch(`${LF_API}/leadforge/campaigns/drafts?campaign_id=${campaignId}`)
      .then(r => r.json()).then(d => setDrafts(d.drafts || d || [])).catch(() => {});
  };

  if (drafts.length === 0) return null;

  const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
    draft: { bg: '#f3f4f6', color: '#6b7280' },
    edited: { bg: '#fef3c7', color: '#d97706' },
    reviewed: { bg: '#dbeafe', color: '#2563eb' },
    sent: { bg: '#dcfce7', color: '#16a34a' },
    failed: { bg: '#fef2f2', color: '#dc2626' },
    skipped: { bg: '#f5f3ef', color: '#999' },
  };

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: '#888' }}>DRAFTS ({drafts.length})</div>
        <button onClick={sendAllReviewed} disabled={sendableDrafts.length === 0}
          style={{ fontSize: 9, padding: '3px 8px', background: sendableDrafts.length === 0 ? '#d1d5db' : '#16a34a', color: '#fff', border: 'none', borderRadius: 4, cursor: sendableDrafts.length === 0 ? 'not-allowed' : 'pointer', fontWeight: 600 }}>
          Send Reviewed ({sendableDrafts.length})
        </button>
      </div>

      {drafts.map(draft => {
        const sc = STATUS_COLORS[draft.status] || STATUS_COLORS.draft;
        return (
          <div key={draft.id} onClick={() => { setSelectedDraft(draft); setEditSubject(draft.subject || ''); setEditBody(draft.body || draft.script || draft.linkedin_message || ''); setEditMode(false); }}
            style={{ padding: '6px 8px', borderBottom: '1px solid #f0ede6', fontSize: 10, cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500 }}>{draft.to_name || `Prospect #${draft.prospect_id}`}</div>
              <div style={{ color: '#888', fontSize: 9 }}>{draft.step_type} — {draft.subject?.slice(0, 40) || 'No subject'}</div>
            </div>
            <span style={{ fontSize: 8, padding: '1px 6px', borderRadius: 4, fontWeight: 600, background: sc.bg, color: sc.color }}>{draft.status}</span>
          </div>
        );
      })}

      {/* Draft detail modal */}
      {selectedDraft && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9990, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setSelectedDraft(null)}>
          <div style={{ background: '#fff', borderRadius: 14, padding: 20, maxWidth: 600, width: '90%', maxHeight: '80vh', overflowY: 'auto' }}
            onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Draft Review</h3>
              <button onClick={() => setSelectedDraft(null)} style={{ background: '#f5f3ef', border: 'none', borderRadius: 6, padding: '4px 8px', cursor: 'pointer' }}>✕</button>
            </div>

            <div style={{ fontSize: 12, marginBottom: 8 }}>
              <strong>To:</strong> {selectedDraft.to_name || 'Unknown'} {selectedDraft.to_email ? `<${selectedDraft.to_email}>` : '(no email)'}
            </div>

            {editMode ? (
              <>
                <div style={{ marginBottom: 8 }}>
                  <label style={{ fontSize: 10, fontWeight: 600, color: '#888' }}>Subject</label>
                  <input value={editSubject} onChange={e => setEditSubject(e.target.value)}
                    style={{ width: '100%', padding: '6px 8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12, marginTop: 2 }} />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <label style={{ fontSize: 10, fontWeight: 600, color: '#888' }}>Body</label>
                  <textarea value={editBody} onChange={e => setEditBody(e.target.value)}
                    rows={12} style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12, lineHeight: 1.5, marginTop: 2 }} />
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button onClick={saveDraftEdit} style={{ padding: '6px 14px', background: '#b8960c', color: '#fff', border: 'none', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>Save Changes</button>
                  <button onClick={() => setEditMode(false)} style={{ padding: '6px 14px', background: '#f5f3ef', color: '#666', border: 'none', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}>Cancel</button>
                </div>
              </>
            ) : (
              <>
                {selectedDraft.subject && (
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, padding: '6px 8px', background: '#faf9f7', borderRadius: 6 }}>
                    Subject: {selectedDraft.subject}
                  </div>
                )}
                <div style={{ fontSize: 12, lineHeight: 1.6, whiteSpace: 'pre-wrap', padding: '10px 12px', background: '#faf9f7', borderRadius: 8, border: '1px solid #e5e2dc', marginBottom: 12, maxHeight: 300, overflowY: 'auto' }}>
                  {selectedDraft.body || selectedDraft.script || selectedDraft.linkedin_message || 'No content'}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {canSendDraft(selectedDraft) && (
                    <button onClick={() => sendDraft(selectedDraft.id)} disabled={sending === selectedDraft.id}
                      style={{ padding: '6px 14px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
                      {sending === selectedDraft.id ? 'Sending...' : '📧 Send via Gmail'}
                    </button>
                  )}
                  {!selectedDraft.to_email && (
                    <span style={{ fontSize: 10, color: '#dc2626', padding: '6px 0' }}>No email address — find and add manually</span>
                  )}
                  {selectedDraft.to_email && !canSendDraft(selectedDraft) && selectedDraft.status !== 'sent' && (
                    <span style={{ fontSize: 10, color: '#b8960c', padding: '6px 0' }}>Review or edit this draft before sending</span>
                  )}
                  <button onClick={() => setEditMode(true)}
                    style={{ padding: '6px 14px', background: '#f5f3ef', color: '#666', border: 'none', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}>
                    ✏️ Edit Draft
                  </button>
                  {selectedDraft.status === 'sent' && (
                    <span style={{ fontSize: 10, color: '#16a34a', fontWeight: 600, padding: '6px 0' }}>✅ Sent {selectedDraft.sent_at?.split('T')[0]}</span>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CampaignsSection() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<any>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [executing, setExecuting] = useState(false);

  const fetchCampaigns = () => {
    fetch(`${LF_API}/leadforge/campaigns`).then(r => r.json()).then(d => {
      setCampaigns(d.campaigns || d || []);
    }).catch(() => {});
  };
  useEffect(() => { fetchCampaigns(); }, []);

  const loadDetail = async (id: number) => {
    const res = await fetch(`${LF_API}/leadforge/campaigns/${id}`);
    const data = await res.json();
    setSelectedCampaign(data);
  };

  const activateCampaign = async (id: number) => {
    await fetch(`${LF_API}/leadforge/campaigns/${id}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'active' }),
    });
    fetchCampaigns();
    if (selectedCampaign?.id === id) loadDetail(id);
  };

  const enrollTop = async (campaignId: number, count: number) => {
    setEnrolling(true);
    // Get top prospects by score
    const pRes = await fetch(`${LF_API}/leadforge/prospects?limit=${count}`);
    const pData = await pRes.json();
    const ids = (pData.prospects || pData || []).map((p: any) => p.id);
    const res = await fetch(`${LF_API}/leadforge/campaigns/${campaignId}/enroll`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prospect_ids: ids }),
    });
    const result = await res.json();
    alert(`Enrolled: ${result.enrolled || 0}, Already: ${result.already_enrolled || 0}, In other: ${result.already_in_other_campaign || 0}`);
    setEnrolling(false);
    loadDetail(campaignId);
    fetchCampaigns();
  };

  const executeCampaigns = async () => {
    setExecuting(true);
    const res = await fetch(`${LF_API}/leadforge/campaigns/execute`, { method: 'POST' });
    const data = await res.json();
    alert(`Executed: ${data.executed || 0}, Skipped: ${data.skipped || 0}, Errors: ${data.errors || 0}`);
    setExecuting(false);
    fetchCampaigns();
    if (selectedCampaign) loadDetail(selectedCampaign.id);
  };

  const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
    draft: { bg: '#f3f4f6', color: '#6b7280' },
    active: { bg: '#dcfce7', color: '#16a34a' },
    paused: { bg: '#fef3c7', color: '#d97706' },
    completed: { bg: '#dbeafe', color: '#2563eb' },
  };

  const STEP_ICONS: Record<string, string> = {
    email: '📧', follow_up_email: '📧', phone_script: '📞', linkedin: '💼', sms: '💬',
  };

  return (
    <div>
      <SH title="Outreach Campaigns" subtitle={`${campaigns.length} campaigns`}
        action={
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={executeCampaigns} disabled={executing}
              style={{ fontSize: 11, padding: '6px 12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
              {executing ? 'Running...' : 'Execute Due Steps'}
            </button>
          </div>
        } />

      {campaigns.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Loading campaigns...</div>
      ) : (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {/* Campaign list */}
          <div style={{ flex: '1 1 300px', minWidth: 0, display: 'grid', gap: 10 }}>
            {campaigns.map((c: any) => {
              const sc = STATUS_COLORS[c.status] || STATUS_COLORS.draft;
              return (
                <div key={c.id} onClick={() => loadDetail(c.id)}
                  style={{ background: '#fff', border: selectedCampaign?.id === c.id ? '2px solid #dc2626' : '1px solid #e5e2dc', borderRadius: 10, padding: 14, cursor: 'pointer' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{c.name}</div>
                    <span style={{ padding: '2px 8px', borderRadius: 8, fontSize: 9, fontWeight: 600, background: sc.bg, color: sc.color }}>{(c.status || 'draft').toUpperCase()}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    {c.prospects_count || 0} enrolled · {c.sent_count || 0} sent · {c.responded_count || 0} responded · Reply: {c.reply_rate || 0}%
                  </div>
                  <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                    {c.status === 'draft' && (
                      <button onClick={e => { e.stopPropagation(); activateCampaign(c.id); }}
                        style={{ fontSize: 9, padding: '2px 8px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>Activate</button>
                    )}
                    <button onClick={e => { e.stopPropagation(); enrollTop(c.id, 10); }} disabled={enrolling}
                      style={{ fontSize: 9, padding: '2px 8px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
                      {enrolling ? '...' : 'Enroll Top 10'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Campaign detail panel */}
          {selectedCampaign && (
            <div style={{ width: 400, maxWidth: '100%', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, flexShrink: 0, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h4 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{selectedCampaign.name}</h4>
                <button onClick={() => setSelectedCampaign(null)} style={{ background: '#f5f3ef', border: 'none', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 11 }}>✕</button>
              </div>

              {/* Stats */}
              {selectedCampaign.analytics && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 12 }}>
                  {[
                    { label: 'Enrolled', value: selectedCampaign.analytics.total_enrolled || 0 },
                    { label: 'Active', value: selectedCampaign.analytics.active || 0 },
                    { label: 'Responded', value: selectedCampaign.analytics.responded || 0 },
                    { label: 'Completed', value: selectedCampaign.analytics.completed || 0 },
                    { label: 'Due Today', value: selectedCampaign.analytics.due_today || 0 },
                    { label: 'Reply %', value: `${selectedCampaign.analytics.reply_rate || 0}%` },
                  ].map((s, i) => (
                    <div key={i} style={{ background: '#faf9f7', borderRadius: 6, padding: 6, textAlign: 'center' }}>
                      <div style={{ fontSize: 16, fontWeight: 700 }}>{s.value}</div>
                      <div style={{ fontSize: 8, color: '#888' }}>{s.label}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Steps */}
              <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 6 }}>SEQUENCE ({(selectedCampaign.steps || []).length} steps)</div>
              {(selectedCampaign.steps || []).map((step: any) => (
                <div key={step.id} style={{ padding: '6px 8px', borderBottom: '1px solid #f0ede6', fontSize: 11, display: 'flex', gap: 6, alignItems: 'center' }}>
                  <span>{STEP_ICONS[step.step_type] || '📋'}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500 }}>{step.subject || step.step_type.replace('_', ' ')}</div>
                    <div style={{ fontSize: 9, color: '#999' }}>Day {step.delay_days} · {step.step_type}{step.is_manual ? ' · ⚡ Manual' : ''}</div>
                  </div>
                </div>
              ))}

              {/* Enrollments preview */}
              <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginTop: 12, marginBottom: 6 }}>
                ENROLLED ({selectedCampaign.enrollment_count || selectedCampaign.enrollment_stats?.total_enrolled || 0})
              </div>
              {(selectedCampaign.enrollment_count || selectedCampaign.enrollment_stats?.total_enrolled || 0) === 0 && (
                <div style={{ fontSize: 11, color: '#999', padding: 8 }}>No prospects enrolled yet</div>
              )}

              {/* Drafts section */}
              <DraftReviewPanel campaignId={selectedCampaign.id} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PipelineRemindersPanel() {
  const [due, setDue] = useState<any>(null);
  const [react, setReact] = useState<any>(null);
  const [open, setOpen] = useState<number | null>(null);
  useEffect(() => {
    fetch(`${LF_API}/followups/due?days_ahead=7`).then(r => r.json()).then(setDue).catch(() => {});
    fetch(`${LF_API}/reactivation?months_quiet=6&limit=15`).then(r => r.json()).then(setReact).catch(() => {});
  }, []);
  const snooze = async (leadId: number, days: number) => {
    await fetch(`${LF_API}/${leadId}/followup`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ in_days: days }) });
    fetch(`${LF_API}/followups/due?days_ahead=7`).then(r => r.json()).then(setDue).catch(() => {});
  };
  const leadRows = due ? [...(due.overdue || []).map((x: any) => ({ ...x, tone: '#dc2626' })), ...(due.due_today || []).map((x: any) => ({ ...x, tone: '#b8960c' })), ...(due.upcoming || []).map((x: any) => ({ ...x, tone: '#2563eb' }))] : [];
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#dc2626', marginBottom: 6 }}>⏰ Pipeline reminders ({leadRows.length})</div>
      {leadRows.length === 0 && <div style={{ fontSize: 11, color: '#999', marginBottom: 8 }}>No lead follow-ups due in the next 7 days.</div>}
      {leadRows.map((f: any) => (
        <div key={f.lead_id} style={{ background: '#fff', border: '1px solid #e5e2dc', borderLeft: `3px solid ${f.tone}`, borderRadius: 8, padding: 10, marginBottom: 6, fontSize: 12, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: '1 1 200px', minWidth: 0 }}>
            <div style={{ fontWeight: 600, overflowWrap: 'anywhere' }}>{f.who}</div>
            <div style={{ color: '#888', fontSize: 11 }}>{f.due} · {f.next_action || 'Follow up'}{f.phone ? ` · ${f.phone}` : ''}</div>
          </div>
          <button onClick={() => snooze(f.lead_id, 2)} style={{ fontSize: 10, padding: '4px 8px', background: '#f5f3ef', border: '1px solid #e5e2dc', borderRadius: 6, cursor: 'pointer' }}>+2 days</button>
          <button onClick={() => snooze(f.lead_id, 7)} style={{ fontSize: 10, padding: '4px 8px', background: '#f5f3ef', border: '1px solid #e5e2dc', borderRadius: 6, cursor: 'pointer' }}>+1 week</button>
        </div>
      ))}
      {due?.quotes_waiting?.length > 0 && (
        <div style={{ fontSize: 11, color: '#666', margin: '6px 0 12px' }}>
          <strong>{due.quotes_waiting.length} sent quotes</strong> waiting on an answer: {due.quotes_waiting.slice(0, 5).map((q: any) => `${q.quote_number} ${q.who || ''}`).join(' · ')}
        </div>
      )}
      <div style={{ fontSize: 11, fontWeight: 700, color: '#7c3aed', margin: '10px 0 6px' }}>♻️ Reactivation — past clients & designers gone quiet ({react?.count ?? 0})</div>
      {(react?.items || []).map((r: any, i: number) => (
        <div key={i} onClick={() => setOpen(open === i ? null : i)} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, padding: 10, marginBottom: 6, fontSize: 12, cursor: 'pointer' }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontWeight: 600 }}>{r.who}</span>
            <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#ede9fe', color: '#7c3aed', fontWeight: 600 }}>{r.kind}</span>
            {r.total_paid > 0 && <span style={{ fontSize: 11, color: '#b8960c', fontWeight: 600 }}>${Math.round(r.total_paid).toLocaleString()}</span>}
          </div>
          <div style={{ color: '#888', fontSize: 11 }}>{(r.why || []).join(' · ')}{r.phone ? ` · ${r.phone}` : ''}{r.email ? ` · ${r.email}` : ''}</div>
          {open === i && <div style={{ marginTop: 6, padding: 8, background: '#faf9f7', borderRadius: 6, whiteSpace: 'pre-wrap' }}><div style={{ fontSize: 9, fontWeight: 700, color: '#b8960c' }}>SUGGESTED TEXT — DRAFT ONLY</div>{r.suggested_message}</div>}
        </div>
      ))}
    </div>
  );
}

function FollowupsSection() {
  const [followups, setFollowups] = useState<any>({});
  useEffect(() => {
    fetch(`${LF_API}/leadforge/campaigns/followups`).then(r => r.json()).then(setFollowups).catch(() => {});
  }, []);
  const due = followups.due_today || [];
  const overdue = followups.overdue || [];
  const upcoming = followups.upcoming_7_days || [];
  return (
    <div>
      <SH title="Follow-up Queue" subtitle={`${due.length} due today, ${overdue.length} overdue, ${upcoming.length} upcoming (campaigns)`} />
      <PipelineRemindersPanel />
      {overdue.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#dc2626', marginBottom: 6 }}>⚠️ Overdue ({overdue.length})</div>
          {overdue.map((f: any) => (
            <div key={f.id} style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: 10, marginBottom: 6, fontSize: 11 }}>
              <div style={{ fontWeight: 600 }}>{f.name || 'Unknown'} — Step {(f.current_step || 0) + 1}: {f.step_type}</div>
              <div style={{ color: '#888', fontSize: 10 }}>Was due: {f.next_step_at?.split('T')[0]}</div>
            </div>
          ))}
        </div>
      )}
      {due.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#b8960c', marginBottom: 6 }}>📋 Due Today ({due.length})</div>
          {due.map((f: any) => (
            <div key={f.id} style={{ background: '#fdf8eb', border: '1px solid #f0e6c0', borderRadius: 8, padding: 10, marginBottom: 6, fontSize: 11 }}>
              <div style={{ fontWeight: 600 }}>{f.name || 'Unknown'} — {f.step_type?.replace('_', ' ')}</div>
              {f.subject && <div style={{ color: '#666', fontSize: 10 }}>Subject: {f.subject}</div>}
            </div>
          ))}
        </div>
      )}
      {upcoming.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#2563eb', marginBottom: 6 }}>📅 Upcoming 7 Days ({upcoming.length})</div>
          {upcoming.map((f: any) => (
            <div key={f.id} style={{ background: '#f5f3ef', borderRadius: 8, padding: 8, marginBottom: 4, fontSize: 10 }}>
              {f.name} — {f.step_type?.replace('_', ' ')} — {f.next_step_at?.split('T')[0]}
            </div>
          ))}
        </div>
      )}
      {due.length === 0 && overdue.length === 0 && upcoming.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No follow-ups scheduled. Activate a campaign and enroll prospects to start.</div>
      )}
    </div>
  );
}

function ActivitySection() {
  const [activity, setActivity] = useState<any[]>([]);
  useEffect(() => {
    fetch(`${LF_API}/leadforge/campaigns/1/activity`).then(r => r.json()).then(d => setActivity(d.activity || d || [])).catch(() => {});
  }, []);
  const ICONS: Record<string, string> = {
    enrolled: '✅', email_sent: '📧', email_drafted: '📧', call_script_ready: '📞',
    linkedin_drafted: '💼', status_changed: '🔄', error: '⚠️', skipped: '⏭️',
  };
  return (
    <div>
      <SH title="Activity Feed" subtitle={`${activity.length} recent activities`} />
      {activity.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Activity will appear here after campaigns execute.</div>
      ) : (
        <div>
          {activity.map((a: any) => (
            <div key={a.id} style={{ padding: '8px 0', borderBottom: '1px solid #f0ede6', fontSize: 11, display: 'flex', gap: 8, alignItems: 'flex-start' }}>
              <span style={{ fontSize: 14 }}>{ICONS[a.action_type] || '📋'}</span>
              <div style={{ flex: 1 }}>
                <div>
                  <span style={{ fontWeight: 600 }}>{a.prospect_name || 'Unknown'}</span>
                  <span style={{ color: '#888' }}> — {(a.action_type || '').replace(/_/g, ' ')}</span>
                </div>
                <div style={{ fontSize: 9, color: '#aaa' }}>{a.created_at?.replace('T', ' ').split('.')[0]}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReportsSection() {
  return (
    <div>
      <SH title="Lead Reports" subtitle="Conversion funnel, source analysis, revenue" />
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
        {[
          { label: 'Conversion Funnel', icon: TrendingUp, desc: 'Lead-to-close pipeline' },
          { label: 'Source Analysis', icon: Globe, desc: 'Which sources produce best leads' },
          { label: 'Revenue Pipeline', icon: DollarSign, desc: 'Projected and closed revenue' },
          { label: 'Activity Report', icon: Activity, desc: 'Calls, emails, meetings per day' },
        ].map((r, i) => (
          <div key={i} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, cursor: 'pointer' }}>
            <r.icon size={20} style={{ color: '#dc2626', marginBottom: 8 }} />
            <div style={{ fontSize: 13, fontWeight: 600 }}>{r.label}</div>
            <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>{r.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
