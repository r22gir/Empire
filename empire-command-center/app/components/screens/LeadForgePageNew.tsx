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
  useEffect(() => { fetch(`${LF_API}?limit=500`).then(r => r.json()).then(d => setLeads(d.leads || d || [])).catch(() => setLeads([])); }, []);

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
      {/* Empty / Loading states */}
      {loading && <div style={{ textAlign: 'center', padding: 30, color: '#999' }}>Loading prospects...</div>}
      {!loading && prospects.length === 0 && <div style={{ textAlign: 'center', padding: 30, color: '#999' }}>No prospects yet — run a search above</div>}

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
                  const fitTags = ['designer_fit', 'upholstery_fit', 'millwork_fit', 'cabinetry_fit', 'hospitality_fit', 'restaurant_fit', 'gc_fit']
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
                  {['designer', 'upholstery', 'millwork', 'cabinetry', 'hospitality', 'restaurant', 'gc'].filter(t => selected[t + '_fit']).map(t =>
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

  useEffect(() => {
    fetch(`${LF_API}/leadforge/campaigns/drafts?campaign_id=${campaignId}`)
      .then(r => r.json()).then(d => setDrafts(d.drafts || d || [])).catch(() => {});
  }, [campaignId]);

  const sendDraft = async (draftId: number) => {
    setSending(draftId);
    try {
      const res = await fetch(`${LF_API}/leadforge/campaigns/drafts/${draftId}/send`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
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
        <button onClick={sendAllReviewed} style={{ fontSize: 9, padding: '3px 8px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}>
          Send All Reviewed
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
                  {selectedDraft.to_email && selectedDraft.status !== 'sent' && (
                    <button onClick={() => sendDraft(selectedDraft.id)} disabled={sending === selectedDraft.id}
                      style={{ padding: '6px 14px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
                      {sending === selectedDraft.id ? 'Sending...' : '📧 Send via Gmail'}
                    </button>
                  )}
                  {!selectedDraft.to_email && (
                    <span style={{ fontSize: 10, color: '#dc2626', padding: '6px 0' }}>No email address — find and add manually</span>
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
  const [followups, setFollowups] = useState<any>({});
  useEffect(() => {
    fetch(`${LF_API}/leadforge/campaigns/followups`).then(r => r.json()).then(setFollowups).catch(() => {});
  }, []);
  const due = followups.due_today || [];
  const overdue = followups.overdue || [];
  const upcoming = followups.upcoming_7_days || [];
  return (
    <div>
      <SH title="Follow-up Queue" subtitle={`${due.length} due today, ${overdue.length} overdue, ${upcoming.length} upcoming`} />
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
