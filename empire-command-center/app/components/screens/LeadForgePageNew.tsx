'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { useTranslation } from '../../lib/i18n';
import {
  Target, Search, Users, Mail, Phone, BarChart3, Calendar,
  Plus, Filter, ChevronRight, Loader2, Send, MessageCircle,
  TrendingUp, AlertTriangle, CheckCircle, Clock, Flame, Snowflake,
  Sun, Eye, Star, ArrowRight, Zap, Globe, MapPin, DollarSign,
  Activity, Crosshair
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import WorkroomLeadForm from '../workroom/WorkroomLeadForm';

const LF_API = `${API}/leads`;

/** Edition trade defaults. Workroom answers {family:false} and keeps its drapery screen. */
interface TradeUnit { value: string; label: string; default_location?: string; default_target?: string; targets?: { value: string; label: string }[]; }
interface TradeProfile { family: boolean; edition?: string; title?: string; subtitle?: string; default_unit?: string; business_units?: TradeUnit[]; fit_tags?: { key: string; label: string; keywords?: string[] }[]; }

let tradeProfileCache: TradeProfile | null = null;

function useTradeProfile(): TradeProfile | null {
  const [profile, setProfile] = useState<TradeProfile | null>(tradeProfileCache);
  useEffect(() => {
    if (tradeProfileCache) return;
    let cancelled = false;
    fetch(`${LF_API}/leadforge/trade-profile`).then(r => (r.ok ? r.json() : { family: false })).then((d: TradeProfile) => {
      tradeProfileCache = d && typeof d === 'object' ? d : { family: false };
      if (!cancelled) setProfile(tradeProfileCache);
    }).catch(() => { if (!cancelled) setProfile({ family: false }); });
    return () => { cancelled = true; };
  }, []);
  return profile;
}

/** Family editions: hide Workroom-only tools and speak Spanish. */
const FAMILY_NAV_LABELS: Record<string, string> = {
  dashboard: 'Tablero', pipeline: 'Embudo', finder: 'Buscar prospectos', campaigns: 'Campañas',
  followups: 'Seguimientos', activity: 'Actividad', reports: 'Reportes', docs: 'Docs',
};

function familyFitTags(p: any, profile: TradeProfile | null): string[] {
  const tags = profile?.fit_tags || [];
  let keys: string[] = [];
  try {
    const mk = Array.isArray(p.matched_keywords) ? p.matched_keywords : JSON.parse(p.matched_keywords || '[]');
    keys = (Array.isArray(mk) ? mk : []).filter((k: any) => typeof k === 'string' && k.startsWith('fit:')).map((k: string) => k.slice(4));
  } catch { keys = []; }
  if (keys.length === 0) {
    const text = `${p.name || ''} ${p.business_name || ''} ${p.category || ''} ${p.description || ''} ${p.snippet || ''}`.toLowerCase();
    keys = tags.filter(t => (t.keywords || []).some(k => text.includes(k))).map(t => t.key);
  }
  return keys.map(k => tags.find(t => t.key === k)?.label || k);
}

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
  const trade = useTradeProfile();
  const family = !!trade?.family;
  const nav = family ? NAV.filter(n => n.id !== 'intake') : NAV;

  useEffect(() => { if (initialSection) setSection(initialSection as Section); }, [initialSection]);
  useEffect(() => { if (family && section === 'intake') setSection('dashboard'); }, [family, section]);

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection />;
      case 'intake': return family ? <DashboardSection /> : <WorkroomIntakeSection />;
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
    <div className={family ? 'lf-root lf-family' : 'lf-root'} style={{ display: 'flex', height: '100%', background: '#faf9f7' }}>
      {family ? (
        <style>{`
          @media (max-width: 820px) {
            .lf-family { flex-direction: column; height: auto !important; min-height: 100%; }
            .lf-family > .lf-side { width: 100% !important; display: flex; overflow-x: auto; overflow-y: hidden !important; white-space: nowrap; border-right: none !important; border-bottom: 1px solid #e5e2dc; padding: 6px 0 !important; }
            .lf-family > .lf-side > .lf-brand { display: none; }
            .lf-family > .lf-side > button { width: auto !important; flex-shrink: 0; }
            .lf-family > .lf-main { overflow: visible !important; padding: 12px !important; }
            .lf-family .lf-main > div > div[style*="gap: 16"] { flex-direction: column; }
            .lf-family .lf-main > div > div[style*="gap: 16"] > div { width: 100% !important; position: static !important; max-height: none !important; }
          }
        `}</style>
      ) : null}
      <div className="lf-side" style={{ width: 200, borderRight: '1px solid #e5e2dc', padding: '16px 0', flexShrink: 0, overflowY: 'auto' }}>
        <div className="lf-brand" style={{ padding: '0 16px 12px', borderBottom: '1px solid #e5e2dc', marginBottom: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#dc2626', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Crosshair size={16} /> {family ? (trade?.title || 'Prospectos') : 'LeadForge'}
          </div>
          <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>{family ? (trade?.subtitle || 'Captación de clientes') : 'AI-Powered Client Acquisition'}</div>
        </div>
        {nav.map(n => (
          <button key={n.id} onClick={() => setSection(n.id)} style={{
            display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '8px 16px',
            border: 'none', cursor: 'pointer', background: section === n.id ? '#fef2f2' : 'transparent',
            color: section === n.id ? '#dc2626' : '#666', fontWeight: section === n.id ? 600 : 400,
            fontSize: 12, textAlign: 'left',
          }}>
            <n.icon size={14} /> {family ? (FAMILY_NAV_LABELS[n.id] || n.label) : n.label}
          </button>
        ))}
      </div>
      <div className="lf-main" style={{ flex: 1, minWidth: 0, overflowY: 'auto', padding: '20px 24px' }}>{renderContent()}</div>
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
  const family = !!useTradeProfile()?.family;
  const [leads, setLeads] = useState<any[]>([]);
  useEffect(() => { fetch(`${LF_API}`).then(r => r.json()).then(d => setLeads(d.leads || d || [])).catch(() => {}); }, []);
  const hot = leads.filter((l: any) => l.temperature === 'hot').length;
  const pipeline = leads.filter((l: any) => !['won', 'lost'].includes(l.status)).reduce((s: number, l: any) => s + (l.estimated_value || 0), 0);
  const won = leads.filter((l: any) => l.status === 'won');
  const winRate = leads.length > 0 ? Math.round(won.length / leads.length * 100) : 0;

  return (
    <div>
      <SH title={family ? 'Tablero de prospectos' : 'LeadForge Dashboard'} subtitle={family ? 'Tu centro de captación de clientes' : 'Your AI-powered sales command center'} />
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <Kpi label={family ? 'Prospectos calientes' : 'Hot Leads'} value={hot} color="#dc2626" />
        <Kpi label={family ? 'Valor en embudo' : 'Pipeline Value'} value={`$${pipeline.toLocaleString()}`} color="#b8960c" />
        <Kpi label={family ? 'Tasa de cierre' : 'Win Rate'} value={`${winRate}%`} color="#16a34a" />
        <Kpi label={family ? 'Total prospectos' : 'Total Leads'} value={leads.length} color="#2563eb" />
      </div>
      {/* AI Recommendation Banner */}
      <div style={{ background: 'linear-gradient(135deg, #fdf8eb, #fff7ed)', border: '1px solid #f5d89a', borderRadius: 10, padding: 14, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
        <Zap size={18} style={{ color: '#b8960c' }} />
        <div style={{ fontSize: 12 }}>
          <span style={{ fontWeight: 600, color: '#b8960c' }}>{family ? 'Asistente:' : 'MAX AI:'}</span>{' '}
          <span style={{ color: '#666' }}>{family ? 'Usa “Buscar prospectos” para encontrar clientes potenciales en tu zona.' : 'Click "Prospect Finder" to discover potential clients in your area using AI-powered web search.'}</span>
        </div>
      </div>
      {/* Recent activity */}
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>{family ? 'Acciones de hoy' : "Today's Actions"}</h3>
        {leads.length === 0 ? (
          <div style={{ fontSize: 12, color: '#999', padding: 16, textAlign: 'center' }}>{family ? 'Aún no hay prospectos. Usa “Buscar prospectos” para empezar.' : 'No leads yet. Use Prospect Finder to start discovering clients.'}</div>
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
  const family = !!useTradeProfile()?.family;
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
      <SH title={family ? 'Embudo de ventas' : 'Sales Pipeline'} subtitle={family ? 'Mueve tus prospectos por el embudo' : 'Drag leads through your sales funnel'}
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> {family ? 'Agregar' : 'Add Lead'}</button>} />
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
                    <span style={{ fontWeight: 600 }}>{lead.first_name} {lead.last_name}</span>
                    {TEMP_ICONS[lead.temperature]}
                  </div>
                  {lead.company && <div style={{ color: '#888', fontSize: 10 }}>{lead.company}</div>}
                  {lead.estimated_value > 0 && <div style={{ color: '#b8960c', fontWeight: 600, fontSize: 10 }}>${lead.estimated_value.toLocaleString()}</div>}
                  <div style={{ fontSize: 10, color: '#666', marginTop: 2 }}>
                    Source: {lead.source || '—'}{lead.utm_campaign ? ` · ${lead.utm_campaign}` : ''}
                  </div>
                  {!family && lead.business_unit === 'workroom' && (
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

function ProspectFinderSection() {
  const trade = useTradeProfile();
  const family = !!trade?.family;
  const units = trade?.business_units || [];
  const [bizUnit, setBizUnit] = useState('workroom');
  const [location, setLocation] = useState('DMV');
  const [target, setTarget] = useState('interior designers');
  const unit = units.find(u => u.value === bizUnit);
  // Family editions start on their own trade, never the Workroom drapery defaults.
  useEffect(() => {
    if (!family || units.length === 0) return;
    const first = units.find(u => u.value === trade?.default_unit) || units[0];
    setBizUnit(first.value);
    setLocation(first.default_location || '');
    setTarget(first.default_target || first.targets?.[0]?.value || '');
  }, [family, trade]); // eslint-disable-line react-hooks/exhaustive-deps
  const pickUnit = (value: string) => {
    setBizUnit(value);
    const u = units.find(x => x.value === value);
    if (family && u) { setLocation(u.default_location || ''); setTarget(u.default_target || u.targets?.[0]?.value || ''); }
  };
  const [searching, setSearching] = useState(false);
  const [prospects, setProspects] = useState<any[]>([]);
  const [searchMeta, setSearchMeta] = useState<any>(null);
  const [pipelineStatus, setPipelineStatus] = useState<Record<number, string>>({});
  const [selected, setSelected] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Load existing prospects + pipeline status on mount
  useEffect(() => {
    Promise.all([
      fetch(`${LF_API}/leadforge/prospects?limit=300`).then(r => r.json()),
      fetch(`${LF_API}/leadforge/prospect-pipeline?limit=500`).then(r => r.json()).catch(() => []),
    ]).then(([prospectData, pipelineData]) => {
      const items = prospectData.prospects || prospectData || [];
      setProspects(items);
      // Build pipeline status from existing pipeline entries
      const pipeItems = pipelineData.pipeline || pipelineData || [];
      const status: Record<number, string> = {};
      for (const pp of pipeItems) {
        if (pp.prospect_id) status[pp.prospect_id] = 'already_in_pipeline';
      }
      setPipelineStatus(status);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const findProspects = async () => {
    setSearching(true);
    try {
      const res = await fetch(`${LF_API}/leadforge/prospects/search`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_unit: bizUnit, location, target_type: target }),
      });
      const data = await res.json();
      setSearchMeta(data);
      // Reload prospects from DB after search
      const listRes = await fetch(`${LF_API}/leadforge/prospects?limit=300`);
      const listData = await listRes.json();
      setProspects(listData.prospects || listData || []);
    } catch { /* keep existing */ }
    setSearching(false);
  };

  const addToPipeline = async (prospectId: number) => {
    try {
      const res = await fetch(`${LF_API}/leadforge/prospects/${prospectId}/pipeline`, { method: 'POST' });
      const data = await res.json();
      setPipelineStatus(prev => ({ ...prev, [prospectId]: data.status }));
    } catch { /* silent */ }
  };

  return (
    <div>
      <SH title={family ? 'Buscar prospectos' : 'Prospect Finder'} subtitle={family ? `${prospects.length} prospectos guardados` : `${prospects.length} prospects in database`} />
      <div style={{ background: 'linear-gradient(135deg, #fef2f2, #fff)', border: '1px solid #fca5a5', borderRadius: 10, padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#dc2626', marginBottom: 10 }}>
          <Crosshair size={14} style={{ verticalAlign: 'text-bottom' }} /> {family ? 'Búsqueda de prospectos reales (Brave + Google + Yelp)' : 'THE WEAPON — Real Prospect Discovery (Brave + Google + Yelp)'}
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
          <div style={{ flex: 1, minWidth: 150 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>{family ? 'Negocio' : 'Business Unit'}</label>
            <select aria-label={family ? 'Negocio' : 'Business Unit'} value={bizUnit} onChange={e => pickUnit(e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12 }}>
              {family ? units.map(u => <option key={u.value} value={u.value}>{u.label}</option>) : (
                <>
                  <option value="workroom">Empire Workroom (Drapery)</option>
                  <option value="woodcraft">WoodCraft (Custom Woodwork)</option>
                  <option value="empire_saas">Empire Box (SaaS)</option>
                </>
              )}
            </select>
          </div>
          <div style={{ flex: 1, minWidth: 150 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>{family ? 'Ubicación' : 'Location'}</label>
            <input aria-label={family ? 'Ubicación' : 'Location'} value={location} onChange={e => setLocation(e.target.value)} placeholder={family ? (unit?.default_location || 'Ciudad, región, país') : 'DMV, Washington DC, nationwide...'}
              style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12 }} />
          </div>
          <div style={{ flex: 1, minWidth: 150 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>{family ? 'Público objetivo' : 'Target Type'}</label>
            {family && unit?.targets?.length ? (
              <select aria-label="Público objetivo" value={target} onChange={e => setTarget(e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12 }}>
                {unit.targets.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            ) : (
              <input value={target} onChange={e => setTarget(e.target.value)} placeholder={family ? 'Tipo de cliente' : 'interior designers, contractors...'}
                style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12 }} />
            )}
          </div>
        </div>
        <button onClick={findProspects} disabled={searching} style={{
          padding: '10px 20px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 8,
          fontWeight: 700, fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {searching ? <Loader2 size={14} className="animate-spin" /> : <Crosshair size={14} />}
          {searching ? (family ? 'Buscando…' : 'Searching...') : (family ? 'Buscar prospectos' : 'Find Prospects')}
        </button>
        {searchMeta && (
          <div style={{ marginTop: 8, fontSize: 10, color: '#888' }}>
            Last search: {searchMeta.raw_result_count || 0} raw → {searchMeta.unique_result_count || 0} unique → {searchMeta.inserted_count || 0} new |
            Providers: {(searchMeta.providers_succeeded || searchMeta.providers_attempted || []).join(', ') || 'none'}
          </div>
        )}
      </div>
      {/* Empty / Loading states */}
      {loading && <div style={{ textAlign: 'center', padding: 30, color: '#999' }}>{family ? 'Cargando prospectos…' : 'Loading prospects...'}</div>}
      {!loading && prospects.length === 0 && <div style={{ textAlign: 'center', padding: 30, color: '#999' }}>{family ? 'Aún no hay prospectos. Haz una búsqueda arriba.' : 'No prospects yet — run a search above'}</div>}

      {/* Prospect table */}
      {prospects.length > 0 && (
        <div style={{ display: 'flex', gap: 16 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>{prospects.length} Prospects</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
                  <th style={{ padding: 6 }}>Name</th>
                  <th style={{ padding: 6 }}>Location</th>
                  <th style={{ padding: 6 }}>Source</th>
                  <th style={{ padding: 6 }}>Score</th>
                  <th style={{ padding: 6 }}>Conf</th>
                  <th style={{ padding: 6 }}>Fit</th>
                  <th style={{ padding: 6 }}>Action</th>
                </tr></thead>
                <tbody>{prospects.map((p: any) => {
                  const inPipeline = pipelineStatus[p.id] === 'added' || pipelineStatus[p.id] === 'already_in_pipeline';
                  const fitTags = family ? familyFitTags(p, trade) : ['designer_fit', 'upholstery_fit', 'millwork_fit', 'cabinetry_fit', 'hospitality_fit', 'restaurant_fit', 'gc_fit']
                    .filter(t => p[t]).map(t => t.replace('_fit', ''));
                  const srcColor = p.source === 'google_places' ? { bg: '#dbeafe', color: '#2563eb' } :
                                   p.source === 'brave' ? { bg: '#fed7aa', color: '#c2410c' } :
                                   p.source === 'yelp' ? { bg: '#fecaca', color: '#dc2626' } : { bg: '#f0fdf4', color: '#16a34a' };
                  return (
                    <tr key={p.id} onClick={() => setSelected(p)}
                      style={{ borderBottom: '1px solid #f0ede6', cursor: 'pointer', background: selected?.id === p.id ? '#fdf8eb' : '' }}
                      onMouseEnter={e => { if (selected?.id !== p.id) e.currentTarget.style.background = '#faf9f7'; }}
                      onMouseLeave={e => { if (selected?.id !== p.id) e.currentTarget.style.background = ''; }}>
                      <td style={{ padding: 6 }}>
                        <div style={{ fontWeight: 500, fontSize: 12 }}>{(p.name || p.business_name || '—').slice(0, 30)}</div>
                        {p.phone && <div style={{ fontSize: 9, color: '#666' }}>{p.phone}</div>}
                      </td>
                      <td style={{ padding: 6, color: '#666', fontSize: 10 }}>{p.location || p.city || '—'}</td>
                      <td style={{ padding: 6 }}><span style={{ fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 4, background: srcColor.bg, color: srcColor.color }}>{p.platform || p.source}</span></td>
                      <td style={{ padding: 6 }}><span style={{ fontWeight: 700, color: (p.score || 0) >= 60 ? '#16a34a' : (p.score || 0) >= 30 ? '#b8960c' : '#999' }}>{p.score || 0}</span></td>
                      <td style={{ padding: 6, fontSize: 10, color: '#888' }}>{p.confidence_score || 0}%</td>
                      <td style={{ padding: 6 }}>
                        <div style={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                          {fitTags.slice(0, 2).map(t => <span key={t} style={{ fontSize: 7, padding: '1px 3px', borderRadius: 3, background: '#fdf8eb', color: '#b8960c', fontWeight: 600 }}>{t}</span>)}
                        </div>
                      </td>
                      <td style={{ padding: 6 }} onClick={e => e.stopPropagation()}>
                        {inPipeline ? (
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

          {/* Detail panel */}
          {selected && (
            <div style={{ width: 320, background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, flexShrink: 0, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)', position: 'sticky', top: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h4 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{selected.name || selected.business_name}</h4>
                <button onClick={() => setSelected(null)} style={{ background: '#f5f3ef', border: 'none', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 11 }}>✕</button>
              </div>

              {/* Contact */}
              <div style={{ fontSize: 11, marginBottom: 12 }}>
                {selected.phone && <div style={{ marginBottom: 2 }}><Phone size={10} style={{ verticalAlign: 'text-bottom' }} /> <a href={`tel:${selected.phone}`} style={{ color: '#2563eb' }}>{selected.phone}</a></div>}
                {selected.website && <div style={{ marginBottom: 2 }}><Globe size={10} style={{ verticalAlign: 'text-bottom' }} /> <a href={selected.website} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb' }}>{selected.website?.replace(/https?:\/\/(www\.)?/, '').slice(0, 30)}</a></div>}
                {selected.address && <div style={{ color: '#666' }}><MapPin size={10} style={{ verticalAlign: 'text-bottom' }} /> {selected.address}</div>}
              </div>

              {/* Score breakdown */}
              <div style={{ background: '#faf9f7', borderRadius: 8, padding: 10, marginBottom: 12, fontSize: 10 }}>
                <div style={{ fontWeight: 700, marginBottom: 4 }}>Score: {selected.score}/100</div>
                <div>Rating: {selected.rating_points || 0}/40 {selected.rating ? `(${selected.rating}★)` : ''}</div>
                <div>Reviews: {selected.review_points || 0}/30 {selected.review_count ? `(${selected.review_count})` : ''}</div>
                <div>Relevance: {selected.relevance_points || 0}/20</div>
                <div>Proximity: {selected.proximity_points || 0}/10</div>
                <div>Keywords: {selected.keyword_bonus || 0}/10</div>
                <div>Source: {selected.source_bonus || 0}/5</div>
                <div style={{ marginTop: 4, fontWeight: 600 }}>Confidence: {selected.confidence_score || 0}%</div>
              </div>

              {/* Fit tags */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 4 }}>FIT TAGS</div>
                <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                  {(family ? familyFitTags(selected, trade) : ['designer', 'upholstery', 'millwork', 'cabinetry', 'hospitality', 'restaurant', 'gc'].filter(t => selected[t + '_fit'])).map(t =>
                    <span key={t} style={{ fontSize: 9, padding: '2px 6px', borderRadius: 4, background: '#fdf8eb', color: '#b8960c', fontWeight: 600 }}>{t}</span>
                  )}
                </div>
              </div>

              {/* Recommended */}
              {selected.recommended_angle && (
                <div style={{ fontSize: 10, color: '#555', marginBottom: 12, fontStyle: 'italic' }}>
                  Angle: {selected.recommended_angle}
                </div>
              )}
              {selected.card_summary && (
                <div style={{ fontSize: 10, color: '#888', marginBottom: 12 }}>{selected.card_summary}</div>
              )}

              {/* Actions */}
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <button onClick={() => addToPipeline(selected.id)} style={{ fontSize: 10, padding: '5px 10px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>+ Pipeline</button>
                {selected.phone && <a href={`tel:${selected.phone}`} style={{ fontSize: 10, padding: '5px 10px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, textDecoration: 'none', fontWeight: 600 }}>Call</a>}
                {selected.website && <a href={selected.website} target="_blank" rel="noopener noreferrer" style={{ fontSize: 10, padding: '5px 10px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, textDecoration: 'none', fontWeight: 600 }}>Website</a>}
              </div>
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
  const family = !!useTradeProfile()?.family;
  const [loaded, setLoaded] = useState(false);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<any>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [executing, setExecuting] = useState(false);

  const fetchCampaigns = () => {
    fetch(`${LF_API}/leadforge/campaigns`).then(r => r.json()).then(d => {
      setCampaigns(d.campaigns || d || []);
    }).catch(() => {}).finally(() => setLoaded(true));
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
      <SH title={family ? 'Campañas de contacto' : 'Outreach Campaigns'} subtitle={family ? `${campaigns.length} campañas` : `${campaigns.length} campaigns`}
        action={
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={executeCampaigns} disabled={executing}
              style={{ fontSize: 11, padding: '6px 12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
              {executing ? (family ? 'Ejecutando…' : 'Running...') : (family ? 'Ejecutar pasos pendientes' : 'Execute Due Steps')}
            </button>
          </div>
        } />

      {campaigns.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{family ? (loaded ? 'Aún no hay campañas.' : 'Cargando campañas…') : 'Loading campaigns...'}</div>
      ) : (
        <div style={{ display: 'flex', gap: 16 }}>
          {/* Campaign list */}
          <div style={{ flex: 1, display: 'grid', gap: 10 }}>
            {campaigns.map((c: any) => {
              const sc = STATUS_COLORS[c.status] || STATUS_COLORS.draft;
              return (
                <div key={c.id} onClick={() => loadDetail(c.id)}
                  style={{ background: '#fff', border: selectedCampaign?.id === c.id ? '2px solid #dc2626' : '1px solid #e5e2dc', borderRadius: 10, padding: 14, cursor: 'pointer' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{c.name}</div>
                    <span style={{ padding: '2px 8px', borderRadius: 8, fontSize: 9, fontWeight: 600, background: sc.bg, color: sc.color }}>{family ? ({ draft: 'BORRADOR', active: 'ACTIVA', paused: 'PAUSADA', completed: 'TERMINADA' } as Record<string, string>)[c.status || 'draft'] || String(c.status).toUpperCase() : (c.status || 'draft').toUpperCase()}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888' }}>
                    {family
                      ? `${c.prospects_count || 0} inscritos · ${c.sent_count || 0} enviados · ${c.responded_count || 0} respondieron · Respuesta: ${c.reply_rate || 0}%`
                      : <>{c.prospects_count || 0} enrolled · {c.sent_count || 0} sent · {c.responded_count || 0} responded · Reply: {c.reply_rate || 0}%</>}
                  </div>
                  <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                    {c.status === 'draft' && (
                      <button onClick={e => { e.stopPropagation(); activateCampaign(c.id); }}
                        style={{ fontSize: 9, padding: '2px 8px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>{family ? 'Activar' : 'Activate'}</button>
                    )}
                    <button onClick={e => { e.stopPropagation(); enrollTop(c.id, 10); }} disabled={enrolling}
                      style={{ fontSize: 9, padding: '2px 8px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
                      {enrolling ? '...' : (family ? 'Inscribir top 10' : 'Enroll Top 10')}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Campaign detail panel */}
          {selectedCampaign && (
            <div style={{ width: 400, background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, flexShrink: 0, overflowY: 'auto', maxHeight: 'calc(100vh - 200px)' }}>
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

function FollowupsSection() {
  const family = !!useTradeProfile()?.family;
  const [followups, setFollowups] = useState<any>({});
  useEffect(() => {
    fetch(`${LF_API}/leadforge/campaigns/followups`).then(r => r.json()).then(setFollowups).catch(() => {});
  }, []);
  const due = followups.due_today || [];
  const overdue = followups.overdue || [];
  const upcoming = followups.upcoming_7_days || [];
  return (
    <div>
      <SH title={family ? 'Seguimientos' : 'Follow-up Queue'} subtitle={family ? `${due.length} para hoy, ${overdue.length} vencidos, ${upcoming.length} próximos` : `${due.length} due today, ${overdue.length} overdue, ${upcoming.length} upcoming`} />
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
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{family ? 'No hay seguimientos programados. Activa una campaña e inscribe prospectos.' : 'No follow-ups scheduled. Activate a campaign and enroll prospects to start.'}</div>
      )}
    </div>
  );
}

function ActivitySection() {
  const trade = useTradeProfile();
  const family = !!trade?.family;
  const [activity, setActivity] = useState<any[]>([]);
  useEffect(() => {
    if (!trade) return;
    if (!trade.family) {
      fetch(`${LF_API}/leadforge/campaigns/1/activity`).then(r => r.json()).then(d => setActivity(d.activity || d || [])).catch(() => {});
      return;
    }
    // Family editions: campaign ids are their own, never assume id 1.
    fetch(`${LF_API}/leadforge/campaigns`).then(r => r.json()).then(async d => {
      const list: any[] = Array.isArray(d?.campaigns) ? d.campaigns : Array.isArray(d) ? d : [];
      const all: any[] = [];
      for (const c of list.slice(0, 10)) {
        const res = await fetch(`${LF_API}/leadforge/campaigns/${c.id}/activity`).then(r => r.json()).catch(() => ({}));
        (Array.isArray(res?.activity) ? res.activity : Array.isArray(res) ? res : []).forEach((a: any) => all.push(a));
      }
      all.sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
      setActivity(all.slice(0, 100));
    }).catch(() => setActivity([]));
  }, [trade]);
  const ICONS: Record<string, string> = {
    enrolled: '✅', email_sent: '📧', email_drafted: '📧', call_script_ready: '📞',
    linkedin_drafted: '💼', status_changed: '🔄', error: '⚠️', skipped: '⏭️',
  };
  return (
    <div>
      <SH title={family ? 'Actividad' : 'Activity Feed'} subtitle={family ? `${activity.length} actividades recientes` : `${activity.length} recent activities`} />
      {activity.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{family ? 'La actividad aparecerá aquí cuando se ejecuten las campañas.' : 'Activity will appear here after campaigns execute.'}</div>
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
  const family = !!useTradeProfile()?.family;
  return (
    <div>
      <SH title={family ? 'Reportes de prospectos' : 'Lead Reports'} subtitle={family ? 'Embudo de conversión, fuentes, ingresos' : 'Conversion funnel, source analysis, revenue'} />
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
