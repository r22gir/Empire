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

const LF_API = `${API}/leads`;

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
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

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection />;
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
    <div style={{ display: 'flex', height: '100%', background: '#faf9f7' }}>
      <div style={{ width: 200, borderRight: '1px solid #e5e2dc', padding: '16px 0', flexShrink: 0, overflowY: 'auto' }}>
        <div style={{ padding: '0 16px 12px', borderBottom: '1px solid #e5e2dc', marginBottom: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#dc2626', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Crosshair size={16} /> LeadForge
          </div>
          <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>AI-Powered Client Acquisition</div>
        </div>
        {NAV.map(n => (
          <button key={n.id} onClick={() => setSection(n.id)} style={{
            display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '8px 16px',
            border: 'none', cursor: 'pointer', background: section === n.id ? '#fef2f2' : 'transparent',
            color: section === n.id ? '#dc2626' : '#666', fontWeight: section === n.id ? 600 : 400,
            fontSize: 12, textAlign: 'left',
          }}>
            <n.icon size={14} /> {n.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>{renderContent()}</div>
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

function PipelineSection() {
  const [leads, setLeads] = useState<any[]>([]);
  useEffect(() => { fetch(`${LF_API}/pipeline`).then(r => r.json()).then(d => setLeads(d.pipeline || d.leads || d || [])).catch(() => setLeads([])); }, []);

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
                    <span style={{ fontWeight: 600 }}>{lead.first_name} {lead.last_name}</span>
                    {TEMP_ICONS[lead.temperature]}
                  </div>
                  {lead.company && <div style={{ color: '#888', fontSize: 10 }}>{lead.company}</div>}
                  {lead.estimated_value > 0 && <div style={{ color: '#b8960c', fontWeight: 600, fontSize: 10 }}>${lead.estimated_value.toLocaleString()}</div>}
                  <div style={{ fontSize: 9, color: '#aaa', marginTop: 2 }}>{lead.source}</div>
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
  const [bizUnit, setBizUnit] = useState('workroom');
  const [location, setLocation] = useState('DMV');
  const [target, setTarget] = useState('interior designers');
  const [searching, setSearching] = useState(false);
  const [prospects, setProspects] = useState<any[]>([]);
  const [searchMeta, setSearchMeta] = useState<any>(null);
  const [pipelineStatus, setPipelineStatus] = useState<Record<number, string>>({});

  // Load existing prospects on mount
  useEffect(() => {
    fetch(`${LF_API}/leadforge/prospects?limit=50&sort_by=score`).then(r => r.json()).then(d => {
      const items = d.prospects || d || [];
      if (items.length > 0) setProspects(items);
    }).catch(() => {});
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
      const listRes = await fetch(`${LF_API}/leadforge/prospects?limit=100&sort_by=score`);
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
      <SH title="Prospect Finder" subtitle={`${prospects.length} prospects in database`} />
      <div style={{ background: 'linear-gradient(135deg, #fef2f2, #fff)', border: '1px solid #fca5a5', borderRadius: 10, padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#dc2626', marginBottom: 10 }}>
          <Crosshair size={14} style={{ verticalAlign: 'text-bottom' }} /> THE WEAPON — Real Prospect Discovery (Brave + Google + Yelp)
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
          <div style={{ flex: 1, minWidth: 150 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Business Unit</label>
            <select value={bizUnit} onChange={e => setBizUnit(e.target.value)} style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12 }}>
              <option value="workroom">Empire Workroom (Drapery)</option>
              <option value="woodcraft">WoodCraft (Custom Woodwork)</option>
              <option value="empire_saas">Empire Box (SaaS)</option>
            </select>
          </div>
          <div style={{ flex: 1, minWidth: 150 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Location</label>
            <input value={location} onChange={e => setLocation(e.target.value)} placeholder="DMV, Washington DC, nationwide..."
              style={{ width: '100%', padding: '8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 12 }} />
          </div>
          <div style={{ flex: 1, minWidth: 150 }}>
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
          <div style={{ marginTop: 8, fontSize: 10, color: '#888' }}>
            Last search: {searchMeta.raw_result_count || 0} raw → {searchMeta.unique_result_count || 0} unique → {searchMeta.inserted_count || 0} new |
            Providers: {(searchMeta.providers_succeeded || searchMeta.providers_attempted || []).join(', ') || 'none'}
          </div>
        )}
      </div>
      {prospects.length > 0 && (
        <div>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>{prospects.length} Prospects</h3>
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
              <th style={{ padding: 8 }}>Name</th>
              <th style={{ padding: 8 }}>Location</th>
              <th style={{ padding: 8 }}>Source</th>
              <th style={{ padding: 8 }}>Score</th>
              <th style={{ padding: 8 }}>Conf</th>
              <th style={{ padding: 8 }}>Fit</th>
              <th style={{ padding: 8 }}>Action</th>
            </tr></thead>
            <tbody>{prospects.map((p: any) => {
              const inPipeline = pipelineStatus[p.id] === 'added' || pipelineStatus[p.id] === 'already_in_pipeline';
              const fitTags = ['designer_fit', 'upholstery_fit', 'millwork_fit', 'cabinetry_fit', 'hospitality_fit', 'restaurant_fit', 'gc_fit']
                .filter(t => p[t]).map(t => t.replace('_fit', ''));
              return (
                <tr key={p.id} style={{ borderBottom: '1px solid #f0ede6' }}>
                  <td style={{ padding: 8 }}>
                    <div style={{ fontWeight: 500 }}>{p.name?.slice(0, 35)}</div>
                    {p.website && <a href={p.website} target="_blank" rel="noopener noreferrer" style={{ fontSize: 10, color: '#2563eb' }}>website</a>}
                  </td>
                  <td style={{ padding: 8, color: '#666', fontSize: 11 }}>{p.location || p.city || '—'}</td>
                  <td style={{ padding: 8 }}><span style={{ fontSize: 9, fontWeight: 600, padding: '1px 6px', borderRadius: 4, background: '#f0fdf4', color: '#16a34a' }}>{p.source || p.platform}</span></td>
                  <td style={{ padding: 8 }}><span style={{ fontWeight: 700, color: (p.score || 0) >= 50 ? '#16a34a' : (p.score || 0) >= 30 ? '#b8960c' : '#999' }}>{p.score || 0}</span></td>
                  <td style={{ padding: 8 }}><span style={{ fontSize: 10, color: (p.confidence_score || 0) >= 75 ? '#16a34a' : '#999' }}>{p.confidence_score || 0}%</span></td>
                  <td style={{ padding: 8 }}>
                    <div style={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                      {fitTags.map(t => <span key={t} style={{ fontSize: 8, padding: '1px 4px', borderRadius: 3, background: '#fdf8eb', color: '#b8960c', fontWeight: 600 }}>{t}</span>)}
                    </div>
                  </td>
                  <td style={{ padding: 8 }}>
                    {inPipeline ? (
                      <span style={{ fontSize: 10, color: '#16a34a', fontWeight: 600 }}>In Pipeline ✓</span>
                    ) : (
                      <button onClick={() => addToPipeline(p.id)} style={{ fontSize: 10, padding: '3px 8px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}>+ Pipeline</button>
                    )}
                  </td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function CampaignsSection() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  useEffect(() => { fetch(`${LF_API}/campaigns`).then(r => r.json()).then(d => setCampaigns(d.campaigns || d || [])).catch(() => {}); }, []);
  return (
    <div>
      <SH title="Outreach Campaigns" subtitle="Automated multi-channel outreach"
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> New Campaign</button>} />
      {campaigns.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No campaigns yet. Create your first outreach campaign.</div> : (
        <div style={{ display: 'grid', gap: 10 }}>
          {campaigns.map((c: any) => (
            <div key={c.id} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{c.name}</div>
                <div style={{ fontSize: 11, color: '#888' }}>{c.channel} — {c.target_audience}</div>
                <div style={{ fontSize: 10, color: '#aaa', marginTop: 4 }}>Sent: {c.sent} | Opened: {c.opened} | Responded: {c.responded} | Converted: {c.converted}</div>
              </div>
              <span style={{ padding: '4px 10px', borderRadius: 12, fontSize: 10, fontWeight: 600, background: c.status === 'active' ? '#f0fdf4' : '#f5f3ef', color: c.status === 'active' ? '#16a34a' : '#888' }}>{c.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FollowupsSection() {
  return <div><SH title="Follow-up Queue" subtitle="Scheduled automated follow-ups" /><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No follow-ups scheduled. Create a campaign to start.</div></div>;
}

function ActivitySection() {
  return <div><SH title="Activity Feed" subtitle="All touchpoints across all leads" /><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Activity will appear here as you interact with leads.</div></div>;
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
