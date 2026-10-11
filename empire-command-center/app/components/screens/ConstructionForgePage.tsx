'use client';
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { API } from '../../lib/api';
import { useTranslation } from '../../lib/i18n';
import {
  Building2, Map, Users, DollarSign, Hammer, HardHat, Package,
  Network, BarChart3, Plus, MapPin, CalendarClock, Pencil, Trash2, X, Layers,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import ViewPdfControl from '../ViewPdfControl';
import UsageCard from '../UsageCard';
import HelpMenu from '../voice/HelpMenu';
import ReservationForm from '../voice/ReservationForm';
import ArchivoCard from '../voice/ArchivoCard';
import ProjectPhotos from '../voice/ProjectPhotos';
import WhatsAppStatus from '../voice/WhatsAppStatus';
import { useAssistantName } from '../../lib/assistant';
import { useEdition } from '../../lib/edition';

const CF_API = `${API}/construction`;

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Tablero', labelEn: 'Dashboard', icon: BarChart3 },
  { id: 'projects', label: 'Proyectos', labelEn: 'Projects', icon: Building2 },
  { id: 'lotmap', label: 'Mapa de Lotes', labelEn: 'Lot Map', icon: Map },
  { id: 'buyers', label: 'Compradores', labelEn: 'Buyers', icon: Users },
  { id: 'sales', label: 'Ventas', labelEn: 'Sales', icon: DollarSign },
  { id: 'payments', label: 'Pagos', labelEn: 'Payments', icon: DollarSign },
  { id: 'plans', label: 'Planes de pago', labelEn: 'Payment plans', icon: CalendarClock },
  { id: 'construction', label: 'Avance de Obra', labelEn: 'Progress', icon: Hammer },
  { id: 'contractors', label: 'Contratistas', labelEn: 'Contractors', icon: HardHat },
  { id: 'materials', label: 'Materiales', labelEn: 'Materials', icon: Package },
  { id: 'infrastructure', label: 'Infraestructura', labelEn: 'Infrastructure', icon: Network },
  { id: 'reports', label: 'Reportes', labelEn: 'Reports', icon: BarChart3 },
  { id: 'docs', label: 'Docs', labelEn: 'Docs', icon: BarChart3 },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

const LOT_STATUS_COLORS: Record<string, string> = {
  available: '#16a34a',
  reserved: '#eab308',
  reservado: '#eab308',
  separado: '#eab308',
  sold: '#2563eb',
  vendido: '#2563eb',
  consultar: '#ea580c',
  under_construction: '#8b5cf6',
  delivered: '#6b7280',
  hold: '#dc2626',
};

const LOT_STATUS_ES: Record<string, string> = {
  available: 'Disponible',
  reserved: 'Separado',
  reservado: 'Separado',
  separado: 'Separado',
  sold: 'Vendido',
  vendido: 'Vendido',
  consultar: 'Consultar',
  under_construction: 'En construcción',
  delivered: 'Entregado',
  hold: 'Retenido',
};

/** Statuses the lot switch offers (backend LOT_STATUSES). */
const LOT_STATUS_OPTIONS = ['available', 'reserved', 'sold', 'consultar', 'under_construction', 'delivered'];
const SELLABLE = ['available', 'reserved', 'consultar'];

/** Backend cf_sales.status values with Spanish labels. */
const SALE_STAGES = [
  { key: 'pending', label: 'Separación (pendiente)', labelEn: 'Reservation (pending)' },
  { key: 'signed', label: 'Promesa firmada', labelEn: 'Contract signed' },
  { key: 'in_progress', label: 'En pagos', labelEn: 'Paying' },
  { key: 'completed', label: 'Escriturada', labelEn: 'Completed' },
  { key: 'cancelled', label: 'Cancelada', labelEn: 'Cancelled' },
];
const SALE_STAGE_ES: Record<string, string> = Object.fromEntries(SALE_STAGES.map(s => [s.key, s.label]));

const PAYMENT_STATUS_ES: Record<string, string> = {
  pending: 'Pendiente', received: 'Recibido', overdue: 'Vencido', cancelled: 'Anulado',
};
const PAYMENT_METHODS = ['transferencia', 'efectivo', 'consignación', 'tarjeta', 'cheque', 'otro'];
const PROJECT_STATUS_ES: Record<string, string> = {
  planning: 'Planeación', active: 'En ventas', under_construction: 'En construcción', completed: 'Terminado', paused: 'Pausado',
};

interface CfProject { id: string; name: string; slug: string; location?: string; description?: string; total_lots?: number; status?: string; currency?: string; }
interface CfLot { id: string; lot_number: string; block?: string; area_m2?: number; frontage_m?: number; depth_m?: number; current_price?: number; base_price?: number; status: string; phase_id?: string; buyer_name?: string; }

interface ConstructionForgePageProps { initialSection?: string; }

// ── helpers ─────────────────────────────────────────────────────────────

function asArray<T = any>(value: any): T[] {
  return Array.isArray(value) ? value : [];
}

async function cf(path: string, init?: RequestInit, absolute = false): Promise<any> {
  const res = await fetch(absolute ? path : `${CF_API}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : `Error ${res.status}`;
    throw new Error(detail);
  }
  return data;
}

const num = (v: string): number | null => {
  if (v === undefined || v === null || String(v).trim() === '') return null;
  const n = Number(String(v).replace(/[^\d.-]/g, ''));
  return Number.isFinite(n) ? n : null;
};

const money = (n: number | null | undefined, currency = 'COP') =>
  currency === 'COP'
    ? `$${Math.round(n || 0).toLocaleString('es-CO')} COP`
    : `$${(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })} ${currency}`;

const naturalLot = (a: CfLot, b: CfLot) =>
  String(a.block || '').localeCompare(String(b.block || ''), 'es', { numeric: true }) ||
  String(a.lot_number || '').localeCompare(String(b.lot_number || ''), 'es', { numeric: true });

const today = () => new Date().toISOString().slice(0, 10);

/** Accept both dashboard shapes: flat fields or {lots:{total,by_status}, payments, construction}. */
function normalizeDashboard(d: any, sitemapLots: CfLot[]) {
  const byStatus: Record<string, number> = (d && d.lots && !Array.isArray(d.lots) && d.lots.by_status) || {};
  const lotList: CfLot[] = Array.isArray(d?.lot_list) ? d.lot_list : Array.isArray(d?.lots) ? d.lots : sitemapLots;
  const count = (s: string) => lotList.filter(l => l.status === s).length;
  const pick = (flat: any, status: string) => (typeof flat === 'number' ? flat : byStatus[status] ?? count(status));
  return {
    total: typeof d?.total_lots === 'number' ? d.total_lots : (d?.lots?.total ?? lotList.length),
    available: pick(d?.available_lots, 'available'),
    reserved: pick(d?.reserved_lots, 'reserved'),
    sold: typeof d?.sold_lots === 'number' ? d.sold_lots : (byStatus.sold ?? count('sold')) + (byStatus.delivered ?? count('delivered')),
    consultar: pick(d?.consultar_lots, 'consultar'),
    collected: d?.revenue_collected ?? d?.payments?.received ?? 0,
    pending: d?.revenue_pending ?? d?.payments?.pending ?? 0,
    progress: d?.construction_progress ?? d?.construction?.avg_progress_percent ?? 0,
    lots: [...lotList].sort(naturalLot),
  };
}

// ── shared UI ───────────────────────────────────────────────────────────

const BTN: React.CSSProperties = { fontSize: 12, padding: '7px 14px', background: '#b8960c', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4 };
const BTN_LIGHT: React.CSSProperties = { ...BTN, background: '#f0ede6', color: '#555' };
const BTN_DANGER: React.CSSProperties = { ...BTN, background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca' };
const CARD: React.CSSProperties = { background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16 };
const INPUT: React.CSSProperties = { width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 13, background: '#fff', boxSizing: 'border-box' };

function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="cf-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, gap: 12, flexWrap: 'wrap' }}>
      <div style={{ minWidth: 0 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>{title}</h2>
        {subtitle && <p style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{subtitle}</p>}
      </div>
      {action ? <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>{action}</div> : null}
    </div>
  );
}

function KpiCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '14px 16px', flex: 1, minWidth: 130 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: color || '#1a1a1a', marginTop: 4, wordBreak: 'break-word' }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function Notice({ msg, error }: { msg: string; error?: boolean }) {
  if (!msg) return null;
  return (
    <div role={error ? 'alert' : 'status'} style={{ fontSize: 12, padding: '8px 12px', borderRadius: 8, marginBottom: 12, background: error ? '#fef2f2' : '#f0fdf4', color: error ? '#b91c1c' : '#15803d', border: `1px solid ${error ? '#fecaca' : '#bbf7d0'}` }}>
      {msg}
    </div>
  );
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 9990, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 12 }} onClick={onClose}>
      <div role="dialog" aria-label={title} style={{ background: '#fff', borderRadius: 14, padding: 18, width: 'min(560px, 96vw)', maxHeight: '90vh', overflowY: 'auto', boxSizing: 'border-box' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{title}</h3>
          <button type="button" aria-label="Cerrar" onClick={onClose} style={{ background: '#f5f3ef', border: 'none', borderRadius: 6, padding: '4px 8px', cursor: 'pointer' }}><X size={14} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children, wide }: { label: string; children: React.ReactNode; wide?: boolean }) {
  return (
    <label style={{ display: 'block', gridColumn: wide ? '1 / -1' : undefined }}>
      <span style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>{label}</span>
      {children}
    </label>
  );
}

function FormGrid({ children }: { children: React.ReactNode }) {
  return <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10, marginBottom: 14 }}>{children}</div>;
}

function StatusPill({ status }: { status: string }) {
  return (
    <span style={{ padding: '2px 8px', borderRadius: 8, fontSize: 10, fontWeight: 700, color: '#fff', background: LOT_STATUS_COLORS[status] || '#999', whiteSpace: 'nowrap' }}>
      {LOT_STATUS_ES[status] || status}
    </span>
  );
}

function LotLegend() {
  return (
    <div style={{ display: 'flex', gap: 12, marginTop: 10, fontSize: 11, flexWrap: 'wrap' }}>
      {[...LOT_STATUS_OPTIONS, 'hold'].map(status => (
        <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 9, height: 9, borderRadius: 2, background: LOT_STATUS_COLORS[status] }} />
          {LOT_STATUS_ES[status]}
        </div>
      ))}
    </div>
  );
}

function NoProject() {
  return <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Selecciona o crea un proyecto para empezar.</div>;
}

function useProjectLots(projectId: string, refreshKey: number) {
  const [lots, setLots] = useState<CfLot[]>([]);
  const [phases, setPhases] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!projectId) { setLots([]); setPhases([]); return; }
    let cancelled = false;
    setLoading(true);
    cf(`/projects/${encodeURIComponent(projectId)}/sitemap`)
      .then(d => { if (!cancelled) { setLots(asArray<CfLot>(d.lots).sort(naturalLot)); setPhases(asArray(d.phases)); } })
      .catch(() => { if (!cancelled) { setLots([]); setPhases([]); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [projectId, refreshKey]);
  return { lots, phases, loading };
}

// ── page ────────────────────────────────────────────────────────────────

export default function ConstructionForgePage({ initialSection }: ConstructionForgePageProps) {
  const [section, setSection] = useState<Section>((initialSection as Section) || 'dashboard');
  const { locale } = useTranslation('construction');
  const assistant = useAssistantName();
  const maxine = useEdition() === 'maxine';
  const [projects, setProjects] = useState<CfProject[]>([]);
  const [projectId, setProjectIdState] = useState<string>('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (initialSection) setSection(initialSection as Section);
  }, [initialSection]);

  const setProjectId = useCallback((id: string) => {
    setProjectIdState(id);
    try { window.localStorage.setItem('cf_project_id', id); } catch { /* private mode */ }
  }, []);

  const loadProjects = useCallback(async () => {
    try {
      const data = await cf('/projects');
      const list = asArray<CfProject>(data.projects ?? data).filter(p => p && p.id !== undefined && p.id !== null && String(p.id) !== '');
      setProjects(list);
      setProjectIdState(current => {
        if (current && list.some(p => String(p.id) === current)) return current;
        let saved = '';
        try { saved = window.localStorage.getItem('cf_project_id') || ''; } catch { /* ignore */ }
        if (saved && list.some(p => String(p.id) === saved)) return saved;
        const biggest = [...list].sort((a, b) => (b.total_lots || 0) - (a.total_lots || 0))[0];
        return biggest ? String(biggest.id) : '';
      });
    } catch {
      setProjects([]);
    }
  }, []);

  useEffect(() => { loadProjects(); }, [loadProjects, refreshKey]);

  const project = projects.find(p => String(p.id) === projectId) || null;
  const bump = () => setRefreshKey(k => k + 1);
  const navLabel = (nav: typeof NAV_SECTIONS[number]) => locale === 'es' ? nav.label : nav.labelEn;
  const projectScoped = !['buyers', 'contractors', 'docs', 'reports', 'projects'].includes(section);

  const renderContent = () => {
    const props = { project, projectId, refreshKey, onChanged: bump };
    switch (section) {
      case 'dashboard': return <DashboardSection {...props} projects={projects} onSelectProject={setProjectId} onOpen={setSection} />;
      case 'projects': return <ProjectsSection projects={projects} onChanged={bump} onSelectProject={(id) => { setProjectId(id); setSection('dashboard'); }} />;
      case 'lotmap': return <LotMapSection {...props} />;
      case 'buyers': return <BuyersSection />;
      case 'sales': return <SalesSection {...props} />;
      case 'payments': return <PaymentsSection {...props} />;
      case 'plans': return <PaymentPlansSection {...props} />;
      case 'construction': return <ProgressSection />;
      case 'contractors': return <ContractorsSection />;
      case 'materials': return <MaterialsSection {...props} />;
      case 'infrastructure': return <InfraSection />;
      case 'reports': return <ReportsSection />;
      case 'docs': return <ProductDocs product="construction" />;
      default: return <DashboardSection {...props} projects={projects} onSelectProject={setProjectId} onOpen={setSection} />;
    }
  };

  return (
    <div className="cf-root cy-module">
      <style>{`
        .cf-root { display: flex; flex: 1; height: 100%; min-height: 0; background: #faf9f7; }
        .cf-side { width: 200px; border-right: 1px solid #e5e2dc; padding: 16px 0; flex-shrink: 0; overflow-y: auto; }
        .cf-side button.cf-nav { display: flex; align-items: center; gap: 8px; width: 100%; padding: 8px 16px; border: none; cursor: pointer; font-size: 12px; text-align: left; }
        .cf-main { flex: 1; min-width: 0; min-height: 0; overflow-y: auto; padding: 20px 24px; }
        .cf-table-wrap { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
        .cf-table-wrap table { min-width: 560px; }
        .cf-lotgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(58px, 1fr)); gap: 6px; flex: 1; min-width: 0; align-content: start; }
        .cf-lotpanel { width: 290px; flex-shrink: 0; }
        .cf-kanban { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 12px; -webkit-overflow-scrolling: touch; }
        @media (max-width: 820px) {
          .cf-root { flex-direction: column; height: auto; min-height: 100%; }
          .cf-side { width: 100%; border-right: none; border-bottom: 1px solid #e5e2dc; padding: 6px 0; display: flex; overflow-x: auto; overflow-y: hidden; white-space: nowrap; -webkit-overflow-scrolling: touch; }
          .cf-side .cf-brand { display: none; }
          .cf-side button.cf-nav { width: auto; flex-shrink: 0; padding: 8px 12px; }
          .cf-main { padding: 12px; overflow: visible; min-height: auto; }
          .cf-lotpanel { width: 100%; }
        }
      `}</style>
      {/* Sidebar */}
      <nav className="cf-side cy-module-nav" aria-label="Portafolio">
        <div className="cf-brand" style={{ padding: '0 16px 12px', borderBottom: '1px solid #e5e2dc', marginBottom: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#b8960c', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Building2 size={16} /> {maxine ? `${assistant}` : 'ConstructionForge'}
          </div>
          <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>
            {maxine ? 'Centro de mando · Portafolio' : (locale === 'es' ? 'Gestión de Desarrollo Inmobiliario' : 'Real Estate Development')}
          </div>
        </div>
        {NAV_SECTIONS.map(nav => (
          <button key={nav.id} type="button" className="cf-nav" onClick={() => setSection(nav.id)}
            style={{
              background: section === nav.id ? '#f0ede6' : 'transparent',
              color: section === nav.id ? '#b8960c' : '#666',
              fontWeight: section === nav.id ? 600 : 400,
            }}>
            <nav.icon size={14} />
            {navLabel(nav)}
          </button>
        ))}
      </nav>

      {/* Main Content */}
      <div className="cf-main cy-module-main">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
          {projectScoped ? (
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#666', flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 600 }}>Proyecto</span>
              <select aria-label="Proyecto" value={projectId} onChange={e => setProjectId(e.target.value)}
                style={{ fontSize: 13, padding: '6px 10px', borderRadius: 6, border: '1px solid #e5e2dc', minWidth: 200, maxWidth: '100%' }}>
                {projects.length === 0 ? <option value="">Sin proyectos</option> : null}
                {projects.map(p => <option key={p.id} value={String(p.id)}>{p.name}</option>)}
              </select>
            </label>
          ) : <span />}
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            {maxine ? <UsageCard /> : null}
            <ViewPdfControl mode="print" title="Imprime la vista actual del portafolio." />
          </div>
        </div>
        {renderContent()}
      </div>
    </div>
  );
}

// === SECTION COMPONENTS ===

interface ScopedProps { project: CfProject | null; projectId: string; refreshKey: number; onChanged: () => void; }

function DashboardSection({ project, projectId, refreshKey, projects, onSelectProject, onOpen }: ScopedProps & { projects: CfProject[]; onSelectProject: (id: string) => void; onOpen: (s: Section) => void }) {
  const { locale } = useTranslation('construction');
  const maxine = useEdition() === 'maxine';
  const [dashboard, setDashboard] = useState<any>(null);
  const [portfolio, setPortfolio] = useState<any[]>([]);
  const [error, setError] = useState('');
  const { lots: sitemapLots } = useProjectLots(projectId, refreshKey);

  useEffect(() => {
    cf('/portfolio').then(data => setPortfolio(asArray(data.projects))).catch(() => setPortfolio([]));
  }, [refreshKey]);

  useEffect(() => {
    if (!projectId) { setDashboard(null); return; }
    let cancelled = false;
    setError('');
    cf(`/projects/${encodeURIComponent(projectId)}/dashboard`)
      .then(d => { if (!cancelled) setDashboard(d); })
      .catch(e => { if (!cancelled) { setDashboard(null); setError(e.message || 'No se pudo cargar el tablero'); } });
    return () => { cancelled = true; };
  }, [projectId, refreshKey]);

  const d = useMemo(() => normalizeDashboard(dashboard || {}, sitemapLots), [dashboard, sitemapLots]);
  const currency = project?.currency || 'COP';

  return (
    <div>
      <SectionHeader
        title={locale === 'es' ? 'Tablero Ejecutivo' : 'Executive Dashboard'}
        subtitle={project ? `${project.name}${project.location ? ` · ${project.location}` : ''}` : ''}
      />
      <Notice msg={error} error />
      {portfolio.length > 0 && (
        <div style={{ display: 'grid', gap: 10, marginBottom: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
          {portfolio.map((card: any) => {
            const active = String(card.id) === projectId;
            return (
              <button key={card.id} type="button" onClick={() => onSelectProject(String(card.id))}
                style={{ textAlign: 'left', background: active ? '#fdf8eb' : '#fff', border: active ? '2px solid #b8960c' : '1px solid #e5e2dc', borderRadius: 10, padding: 12, cursor: 'pointer' }}>
                <strong>{card.name}</strong>
                <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>{card.location} · {card.lot_count} lotes</div>
                <div style={{ fontSize: 12, color: '#444', marginTop: 4 }}>
                  {Object.entries(card.lots_by_status || {}).map(([status, count]) => `${LOT_STATUS_ES[status] || status}: ${count}`).join(' · ') || 'Sin lotes'}
                </div>
                <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
                  Pagos por cobrar: {card.payments_due ?? 0}
                  {card.construction_progress != null ? ` · Avance ${card.construction_progress}%` : ''}
                </div>
              </button>
            );
          })}
        </div>
      )}
      {!projectId && projects.length === 0 ? <NoProject /> : null}
      {maxine ? (
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16, alignItems: 'flex-start' }}>
          <HelpMenu />
          <ArchivoCard />
          <WhatsAppStatus />
        </div>
      ) : null}
      {maxine ? <ReservationForm /> : null}
      <div data-testid="cf-kpis" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        <KpiCard label="Total lotes" value={projectId ? d.total : '—'} />
        <KpiCard label={locale === 'es' ? 'Lotes Disponibles' : 'Available Lots'} value={projectId ? d.available : '—'} color={LOT_STATUS_COLORS.available} />
        <KpiCard label="Separados" value={projectId ? d.reserved : '—'} color="#a16207" />
        <KpiCard label={locale === 'es' ? 'Lotes Vendidos' : 'Lots Sold'} value={projectId ? d.sold : '—'} color={LOT_STATUS_COLORS.sold} />
        <KpiCard label="Consultar" value={projectId ? d.consultar : '—'} color={LOT_STATUS_COLORS.consultar} />
      </div>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 20 }}>
        <KpiCard label={locale === 'es' ? 'Ingresos Recaudados' : 'Revenue Collected'} value={money(d.collected, currency)} color="#b8960c" />
        <KpiCard label={locale === 'es' ? 'Ingresos Pendientes' : 'Revenue Pending'} value={money(d.pending, currency)} />
        <KpiCard label={locale === 'es' ? 'Avance de Obra' : 'Construction Progress'} value={`${d.progress ?? 0}%`} color="#8b5cf6" />
      </div>

      <div style={{ ...CARD, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 8, flexWrap: 'wrap' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>{locale === 'es' ? 'Estado de Lotes' : 'Lot Status'}</h3>
          <button type="button" style={BTN_LIGHT} onClick={() => onOpen('lotmap')}><Map size={12} /> Ver mapa de lotes</button>
        </div>
        {d.lots.length === 0 ? (
          <div style={{ fontSize: 12, color: '#999' }}>{projectId ? 'Este proyecto aún no tiene lotes.' : ''}</div>
        ) : (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {d.lots.slice(0, 200).map((lot: CfLot) => (
              <div key={lot.id || lot.lot_number} onClick={() => onOpen('lotmap')} style={{
                minWidth: 30, height: 30, padding: '0 4px', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 9, fontWeight: 700, color: '#fff', cursor: 'pointer',
                background: LOT_STATUS_COLORS[lot.status] || '#999',
              }} title={`Lote ${lot.lot_number} — ${LOT_STATUS_ES[lot.status] || lot.status}`}>
                {String(lot.lot_number || '').replace(/^L-/, '')}
              </div>
            ))}
          </div>
        )}
        <LotLegend />
      </div>
    </div>
  );
}

const EMPTY_PROJECT = { name: '', location: '', description: '', total_lots: '', status: 'planning', currency: 'COP' };

function ProjectsSection({ projects, onChanged, onSelectProject }: { projects: CfProject[]; onChanged: () => void; onSelectProject: (id: string) => void }) {
  const { locale } = useTranslation('construction');
  const [editing, setEditing] = useState<CfProject | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<any>(EMPTY_PROJECT);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const startCreate = () => { setEditing(null); setForm(EMPTY_PROJECT); setErr(''); setOpen(true); };
  const startEdit = (p: CfProject) => {
    setEditing(p);
    setForm({ name: p.name || '', location: p.location || '', description: p.description || '', total_lots: p.total_lots ?? '', status: p.status || 'planning', currency: p.currency || 'COP' });
    setErr(''); setOpen(true);
  };
  const save = async () => {
    if (!form.name.trim()) { setErr('El nombre del proyecto es obligatorio.'); return; }
    setBusy(true); setErr('');
    const body = { name: form.name.trim(), location: form.location, description: form.description, total_lots: num(String(form.total_lots)) ?? 0, status: form.status, currency: form.currency || 'COP' };
    try {
      if (editing) await cf(`/projects/${encodeURIComponent(editing.id)}`, { method: 'PUT', body: JSON.stringify(body) });
      else await cf('/projects', { method: 'POST', body: JSON.stringify(body) });
      setOpen(false); setMsg(editing ? 'Proyecto actualizado.' : 'Proyecto creado.'); onChanged();
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Proyectos' : 'Projects'}
        action={<button type="button" style={BTN} onClick={startCreate}><Plus size={12} /> {locale === 'es' ? 'Nuevo Proyecto' : 'New Project'}</button>} />
      <Notice msg={msg} />
      {projects.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'No hay proyectos. Crea el primero.' : 'No projects. Create the first one.'}</div>
      ) : projects.map(p => (
        <div key={p.id} style={{ ...CARD, marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 600 }}>{p.name}</div>
              <div style={{ fontSize: 11, color: '#888', display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                <MapPin size={10} /> {p.location || '—'}
              </div>
            </div>
            <div style={{ padding: '4px 10px', borderRadius: 12, fontSize: 10, fontWeight: 600, background: '#f0ede6', color: '#b8960c' }}>
              {PROJECT_STATUS_ES[p.status || ''] || p.status}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: '#666', alignItems: 'center', flexWrap: 'wrap' }}>
            <span>{p.total_lots ?? 0} lotes</span>
            <span>{p.currency}</span>
            <span style={{ flex: 1 }} />
            <button type="button" style={BTN_LIGHT} onClick={() => onSelectProject(String(p.id))}>Abrir tablero</button>
            <button type="button" style={BTN_LIGHT} onClick={() => startEdit(p)}><Pencil size={12} /> Editar</button>
          </div>
        </div>
      ))}
      {open && (
        <Modal title={editing ? 'Editar proyecto' : 'Nuevo proyecto'} onClose={() => setOpen(false)}>
          <Notice msg={err} error />
          <FormGrid>
            <Field label="Nombre *" wide><input style={INPUT} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Ubicación" wide><input style={INPUT} value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} /></Field>
            <Field label="Total de lotes"><input style={INPUT} inputMode="numeric" value={form.total_lots} onChange={e => setForm({ ...form, total_lots: e.target.value })} /></Field>
            <Field label="Estado">
              <select style={INPUT} value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                {Object.entries(PROJECT_STATUS_ES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </Field>
            <Field label="Moneda">
              <select style={INPUT} value={form.currency} onChange={e => setForm({ ...form, currency: e.target.value })}>
                <option value="COP">COP</option><option value="USD">USD</option>
              </select>
            </Field>
            <Field label="Descripción" wide><textarea style={{ ...INPUT, minHeight: 70 }} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></Field>
          </FormGrid>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" style={BTN_LIGHT} onClick={() => setOpen(false)}>Cancelar</button>
            <button type="button" style={BTN} disabled={busy} onClick={save}>{busy ? 'Guardando…' : 'Guardar'}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Lot map ─────────────────────────────────────────────────────────────

const EMPTY_LOT = { lot_number: '', block: '', phase_id: '', area_m2: '', frontage_m: '', depth_m: '', current_price: '', status: 'available' };
const EMPTY_BULK = { prefix: 'L-', start_number: '1', count: '10', block: '', phase_id: '', area_m2: '', current_price: '', status: 'available' };

function LotMapSection({ project, projectId, refreshKey, onChanged }: ScopedProps) {
  const { locale } = useTranslation('construction');
  const { lots, phases, loading } = useProjectLots(projectId, refreshKey);
  const [filter, setFilter] = useState('all');
  const [phaseFilter, setPhaseFilter] = useState('all');
  const [selected, setSelected] = useState<CfLot | null>(null);
  const [lotModal, setLotModal] = useState<null | 'new' | 'edit'>(null);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [form, setForm] = useState<any>(EMPTY_LOT);
  const [bulk, setBulk] = useState<any>(EMPTY_BULK);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const currency = project?.currency || 'COP';

  useEffect(() => {
    // keep the side panel in sync after a refresh
    setSelected(prev => (prev ? lots.find(l => l.id === prev.id) || null : null));
  }, [lots]);

  if (!projectId) return <NoProject />;

  const visible = lots.filter(l => (filter === 'all' || l.status === filter) && (phaseFilter === 'all' || String(l.phase_id || '') === phaseFilter));
  const counts: Record<string, number> = {};
  lots.forEach(l => { counts[l.status] = (counts[l.status] || 0) + 1; });

  const changeStatus = async (lot: CfLot, status: string) => {
    setErr(''); setMsg('');
    try {
      await cf(`/lots/${encodeURIComponent(lot.id)}/status`, { method: 'PATCH', body: JSON.stringify({ status }) });
      setMsg(`Lote ${lot.lot_number}: ${LOT_STATUS_ES[status] || status}.`);
      onChanged();
    } catch (e: any) { setErr(e.message); }
  };

  const openNew = () => { setForm(EMPTY_LOT); setErr(''); setLotModal('new'); };
  const openEdit = (lot: CfLot) => {
    setForm({
      lot_number: lot.lot_number || '', block: lot.block || '', phase_id: lot.phase_id || '',
      area_m2: lot.area_m2 ?? '', frontage_m: lot.frontage_m ?? '', depth_m: lot.depth_m ?? '',
      current_price: lot.current_price ?? '', status: lot.status,
    });
    setErr(''); setLotModal('edit');
  };

  const saveLot = async () => {
    if (!String(form.lot_number).trim()) { setErr('El número de lote es obligatorio.'); return; }
    setBusy(true); setErr('');
    const price = num(String(form.current_price)) ?? 0;
    const body: any = {
      lot_number: String(form.lot_number).trim(), block: form.block || null, phase_id: form.phase_id || null,
      area_m2: num(String(form.area_m2)), frontage_m: num(String(form.frontage_m)), depth_m: num(String(form.depth_m)),
      current_price: price,
    };
    try {
      if (lotModal === 'edit' && selected) {
        await cf(`/lots/${encodeURIComponent(selected.id)}`, { method: 'PUT', body: JSON.stringify(body) });
        if (form.status !== selected.status) {
          await cf(`/lots/${encodeURIComponent(selected.id)}/status`, { method: 'PATCH', body: JSON.stringify({ status: form.status }) });
        }
        setMsg(`Lote ${body.lot_number} actualizado.`);
      } else {
        await cf(`/projects/${encodeURIComponent(projectId)}/lots`, { method: 'POST', body: JSON.stringify({ ...body, base_price: price, status: form.status }) });
        setMsg(`Lote ${body.lot_number} creado.`);
      }
      setLotModal(null); onChanged();
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  const saveBulk = async () => {
    const count = num(String(bulk.count)) ?? 0;
    const start = num(String(bulk.start_number)) ?? 1;
    if (count < 1 || count > 500) { setErr('La cantidad debe estar entre 1 y 500.'); return; }
    setBusy(true); setErr('');
    const price = num(String(bulk.current_price)) ?? 0;
    try {
      const res = await cf(`/projects/${encodeURIComponent(projectId)}/lots/bulk`, {
        method: 'POST',
        body: JSON.stringify({
          prefix: bulk.prefix || '', start_number: start, count, block: bulk.block || null, phase_id: bulk.phase_id || null,
          area_m2: num(String(bulk.area_m2)), base_price: price, current_price: price, status: bulk.status,
        }),
      });
      const skipped = asArray(res.skipped_existing);
      setMsg(`${res.created ?? 0} lotes creados${skipped.length ? ` · ${skipped.length} ya existían (omitidos)` : ''}.`);
      setBulkOpen(false); onChanged();
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  const deleteLot = async (lot: CfLot) => {
    if (!window.confirm(`¿Eliminar el lote ${lot.lot_number}? Esta acción no se puede deshacer.`)) return;
    setErr(''); setMsg('');
    try {
      await cf(`/lots/${encodeURIComponent(lot.id)}`, { method: 'DELETE' });
      setSelected(null); setMsg(`Lote ${lot.lot_number} eliminado.`); onChanged();
    } catch (e: any) { setErr(e.message); }
  };

  const phaseName = (id?: string) => phases.find((p: any) => String(p.id) === String(id || ''))?.name || '';

  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Mapa de Lotes' : 'Lot Map'}
        subtitle={`${project?.name || ''} · ${lots.length} lotes`}
        action={<>
          <button type="button" style={BTN_LIGHT} onClick={() => { setBulk(EMPTY_BULK); setErr(''); setBulkOpen(true); }}><Layers size={12} /> Crear varios</button>
          <button type="button" style={BTN} onClick={openNew}><Plus size={12} /> Nuevo lote</button>
        </>} />
      <Notice msg={msg} />
      {!lotModal && !bulkOpen ? <Notice msg={err} error /> : null}
      <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        {['all', ...LOT_STATUS_OPTIONS].map(s => (
          <button key={s} type="button" onClick={() => setFilter(s)} style={{
            fontSize: 11, padding: '4px 10px', borderRadius: 12, cursor: 'pointer',
            border: filter === s ? `2px solid ${LOT_STATUS_COLORS[s] || '#b8960c'}` : '1px solid #e5e2dc',
            background: filter === s ? '#fdf8eb' : '#fff', fontWeight: filter === s ? 600 : 400,
          }}>
            {s === 'all' ? `Todos (${lots.length})` : `${LOT_STATUS_ES[s]} (${counts[s] || 0})`}
          </button>
        ))}
        {phases.length > 0 && (
          <select aria-label="Etapa" value={phaseFilter} onChange={e => setPhaseFilter(e.target.value)} style={{ ...INPUT, width: 'auto', fontSize: 11, padding: '4px 8px' }}>
            <option value="all">Todas las etapas</option>
            {phases.map((p: any) => <option key={p.id} value={String(p.id)}>{p.name}</option>)}
          </select>
        )}
      </div>
      {loading && lots.length === 0 ? <div style={{ color: '#999', fontSize: 12 }}>Cargando lotes…</div> : null}
      {!loading && lots.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Este proyecto aún no tiene lotes. Usa “Nuevo lote” o “Crear varios”.</div>
      ) : (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div className="cf-lotgrid" data-testid="cf-lotgrid">
            {visible.map(lot => (
              <button key={lot.id} type="button" onClick={() => setSelected(lot)} title={`Lote ${lot.lot_number} — ${LOT_STATUS_ES[lot.status] || lot.status}`} style={{
                height: 52, borderRadius: 6, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 700, color: '#fff', cursor: 'pointer', padding: 2,
                background: LOT_STATUS_COLORS[lot.status] || '#999',
                border: selected?.id === lot.id ? '3px solid #1a1a1a' : '2px solid transparent',
              }}>
                <span>{lot.lot_number}</span>
                {lot.area_m2 ? <span style={{ fontSize: 8, opacity: 0.85 }}>{lot.area_m2} m²</span> : null}
              </button>
            ))}
          </div>
          {selected && (
            <div className="cf-lotpanel" style={CARD}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Lote {selected.lot_number}</h3>
                <StatusPill status={selected.status} />
              </div>
              <div style={{ fontSize: 12, color: '#555', marginTop: 10, display: 'grid', gap: 4 }}>
                {phaseName(selected.phase_id) ? <div>Etapa: <strong>{phaseName(selected.phase_id)}</strong></div> : null}
                {selected.block ? <div>Manzana: <strong>{selected.block}</strong></div> : null}
                <div>Área: <strong>{selected.area_m2 ? `${selected.area_m2} m²` : '—'}</strong></div>
                {(selected.frontage_m || selected.depth_m) ? <div>Frente × fondo: <strong>{selected.frontage_m || '—'} × {selected.depth_m || '—'} m</strong></div> : null}
                <div>Precio: <strong>{selected.current_price ? money(selected.current_price, currency) : 'Consultar'}</strong></div>
                {selected.buyer_name ? <div>Comprador: <strong>{selected.buyer_name}</strong></div> : null}
              </div>
              <label style={{ display: 'block', marginTop: 12 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: '#666' }}>Cambiar estado</span>
                <select aria-label="Estado del lote" value={selected.status} onChange={e => changeStatus(selected, e.target.value)} style={{ ...INPUT, marginTop: 4 }}>
                  {LOT_STATUS_OPTIONS.map(s => <option key={s} value={s}>{LOT_STATUS_ES[s]}</option>)}
                  {!LOT_STATUS_OPTIONS.includes(selected.status) ? <option value={selected.status}>{LOT_STATUS_ES[selected.status] || selected.status}</option> : null}
                </select>
              </label>
              <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                <button type="button" style={BTN_LIGHT} onClick={() => openEdit(selected)}><Pencil size={12} /> Editar</button>
                <button type="button" style={BTN_DANGER} onClick={() => deleteLot(selected)}><Trash2 size={12} /> Eliminar</button>
              </div>
            </div>
          )}
        </div>
      )}
      <LotLegend />

      {lotModal && (
        <Modal title={lotModal === 'edit' ? `Editar lote ${selected?.lot_number || ''}` : 'Nuevo lote'} onClose={() => setLotModal(null)}>
          <Notice msg={err} error />
          <FormGrid>
            <Field label="Número de lote *"><input style={INPUT} value={form.lot_number} onChange={e => setForm({ ...form, lot_number: e.target.value })} placeholder="L-28" /></Field>
            <Field label="Estado">
              <select style={INPUT} value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                {LOT_STATUS_OPTIONS.map(s => <option key={s} value={s}>{LOT_STATUS_ES[s]}</option>)}
              </select>
            </Field>
            {phases.length > 0 && (
              <Field label="Etapa">
                <select style={INPUT} value={form.phase_id} onChange={e => setForm({ ...form, phase_id: e.target.value })}>
                  <option value="">Sin etapa</option>
                  {phases.map((p: any) => <option key={p.id} value={String(p.id)}>{p.name}</option>)}
                </select>
              </Field>
            )}
            <Field label="Manzana"><input style={INPUT} value={form.block} onChange={e => setForm({ ...form, block: e.target.value })} /></Field>
            <Field label="Área (m²)"><input style={INPUT} inputMode="decimal" value={form.area_m2} onChange={e => setForm({ ...form, area_m2: e.target.value })} /></Field>
            <Field label="Frente (m)"><input style={INPUT} inputMode="decimal" value={form.frontage_m} onChange={e => setForm({ ...form, frontage_m: e.target.value })} /></Field>
            <Field label="Fondo (m)"><input style={INPUT} inputMode="decimal" value={form.depth_m} onChange={e => setForm({ ...form, depth_m: e.target.value })} /></Field>
            <Field label={`Precio (${currency})`}><input style={INPUT} inputMode="numeric" value={form.current_price} onChange={e => setForm({ ...form, current_price: e.target.value })} placeholder="0 = consultar" /></Field>
          </FormGrid>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" style={BTN_LIGHT} onClick={() => setLotModal(null)}>Cancelar</button>
            <button type="button" style={BTN} disabled={busy} onClick={saveLot}>{busy ? 'Guardando…' : 'Guardar lote'}</button>
          </div>
        </Modal>
      )}

      {bulkOpen && (
        <Modal title="Crear varios lotes" onClose={() => setBulkOpen(false)}>
          <Notice msg={err} error />
          <p style={{ fontSize: 12, color: '#666', marginTop: 0 }}>Se crean lotes numerados consecutivamente. Los números que ya existen se omiten.</p>
          <FormGrid>
            <Field label="Prefijo"><input style={INPUT} value={bulk.prefix} onChange={e => setBulk({ ...bulk, prefix: e.target.value })} /></Field>
            <Field label="Desde el número"><input style={INPUT} inputMode="numeric" value={bulk.start_number} onChange={e => setBulk({ ...bulk, start_number: e.target.value })} /></Field>
            <Field label="Cantidad"><input style={INPUT} inputMode="numeric" value={bulk.count} onChange={e => setBulk({ ...bulk, count: e.target.value })} /></Field>
            <Field label="Estado">
              <select style={INPUT} value={bulk.status} onChange={e => setBulk({ ...bulk, status: e.target.value })}>
                {LOT_STATUS_OPTIONS.map(s => <option key={s} value={s}>{LOT_STATUS_ES[s]}</option>)}
              </select>
            </Field>
            {phases.length > 0 && (
              <Field label="Etapa">
                <select style={INPUT} value={bulk.phase_id} onChange={e => setBulk({ ...bulk, phase_id: e.target.value })}>
                  <option value="">Sin etapa</option>
                  {phases.map((p: any) => <option key={p.id} value={String(p.id)}>{p.name}</option>)}
                </select>
              </Field>
            )}
            <Field label="Manzana"><input style={INPUT} value={bulk.block} onChange={e => setBulk({ ...bulk, block: e.target.value })} /></Field>
            <Field label="Área (m²)"><input style={INPUT} inputMode="decimal" value={bulk.area_m2} onChange={e => setBulk({ ...bulk, area_m2: e.target.value })} /></Field>
            <Field label={`Precio (${currency})`}><input style={INPUT} inputMode="numeric" value={bulk.current_price} onChange={e => setBulk({ ...bulk, current_price: e.target.value })} /></Field>
          </FormGrid>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 10 }}>
            Vista previa: {bulk.prefix}{bulk.start_number} … {bulk.prefix}{(num(String(bulk.start_number)) ?? 1) + Math.max((num(String(bulk.count)) ?? 1) - 1, 0)}
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" style={BTN_LIGHT} onClick={() => setBulkOpen(false)}>Cancelar</button>
            <button type="button" style={BTN} disabled={busy} onClick={saveBulk}>{busy ? 'Creando…' : 'Crear lotes'}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Buyers ──────────────────────────────────────────────────────────────

const EMPTY_BUYER = { first_name: '', last_name: '', cedula: '', email: '', phone: '', whatsapp: '', city: '', country: 'Colombia', referral_source: '', notes: '' };

function BuyerFormModal({ buyer, onClose, onSaved }: { buyer: any | null; onClose: () => void; onSaved: (b: any) => void }) {
  const [form, setForm] = useState<any>(() => buyer ? Object.fromEntries(Object.keys(EMPTY_BUYER).map(k => [k, buyer[k] ?? ''])) : EMPTY_BUYER);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: e.target.value });
  const save = async () => {
    if (!form.first_name.trim() || !form.last_name.trim()) { setErr('Nombre y apellido son obligatorios.'); return; }
    setBusy(true); setErr('');
    const body = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, typeof v === 'string' ? (v.trim() || (k === 'country' ? 'Colombia' : null)) : v]));
    try {
      const saved = buyer
        ? await cf(`/buyers/${encodeURIComponent(buyer.id)}`, { method: 'PUT', body: JSON.stringify(body) })
        : await cf('/buyers', { method: 'POST', body: JSON.stringify(body) });
      onSaved(saved);
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };
  return (
    <Modal title={buyer ? 'Editar comprador' : 'Nuevo comprador'} onClose={onClose}>
      <Notice msg={err} error />
      <FormGrid>
        <Field label="Nombre *"><input style={INPUT} value={form.first_name} onChange={set('first_name')} /></Field>
        <Field label="Apellido *"><input style={INPUT} value={form.last_name} onChange={set('last_name')} /></Field>
        <Field label="Cédula"><input style={INPUT} value={form.cedula} onChange={set('cedula')} /></Field>
        <Field label="Correo"><input style={INPUT} type="email" value={form.email} onChange={set('email')} /></Field>
        <Field label="Teléfono"><input style={INPUT} type="tel" value={form.phone} onChange={set('phone')} /></Field>
        <Field label="WhatsApp"><input style={INPUT} type="tel" value={form.whatsapp} onChange={set('whatsapp')} /></Field>
        <Field label="Ciudad"><input style={INPUT} value={form.city} onChange={set('city')} /></Field>
        <Field label="País"><input style={INPUT} value={form.country} onChange={set('country')} /></Field>
        <Field label="¿Cómo nos conoció?" wide><input style={INPUT} value={form.referral_source} onChange={set('referral_source')} placeholder="Referido, redes sociales, valla…" /></Field>
        <Field label="Notas" wide><textarea style={{ ...INPUT, minHeight: 60 }} value={form.notes} onChange={set('notes')} /></Field>
      </FormGrid>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button type="button" style={BTN_LIGHT} onClick={onClose}>Cancelar</button>
        <button type="button" style={BTN} disabled={busy} onClick={save}>{busy ? 'Guardando…' : 'Guardar comprador'}</button>
      </div>
    </Modal>
  );
}

function BuyersSection() {
  const { locale } = useTranslation('construction');
  const [buyers, setBuyers] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState<any | null>(null);
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(() => {
    const q = search.trim() ? `?search=${encodeURIComponent(search.trim())}` : '';
    cf(`/buyers${q}`).then(d => setBuyers(asArray(d.buyers ?? d))).catch(() => setBuyers([]));
  }, [search]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);

  const remove = async (b: any) => {
    if (!window.confirm(`¿Eliminar a ${b.first_name} ${b.last_name}?`)) return;
    setErr(''); setMsg('');
    try { await cf(`/buyers/${encodeURIComponent(b.id)}`, { method: 'DELETE' }); setMsg('Comprador eliminado.'); load(); }
    catch (e: any) { setErr(e.message); }
  };

  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Compradores' : 'Buyers'} subtitle={`${buyers.length} registrados`}
        action={<button type="button" style={BTN} onClick={() => { setEditing(null); setOpen(true); }}><Plus size={12} /> {locale === 'es' ? 'Nuevo Comprador' : 'New Buyer'}</button>} />
      <Notice msg={msg} /><Notice msg={err} error />
      <input aria-label="Buscar comprador" style={{ ...INPUT, maxWidth: 360, marginBottom: 12 }} placeholder="Buscar por nombre, cédula o correo…" value={search} onChange={e => setSearch(e.target.value)} />
      {buyers.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{search ? 'Sin resultados.' : (locale === 'es' ? 'No hay compradores registrados.' : 'No buyers registered.')}</div>
      ) : (
        <div className="cf-table-wrap">
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
              <th style={{ padding: 8 }}>Nombre</th><th style={{ padding: 8 }}>Cédula</th><th style={{ padding: 8 }}>Teléfono / WhatsApp</th><th style={{ padding: 8 }}>Correo</th><th style={{ padding: 8 }}>Ciudad</th><th style={{ padding: 8 }} />
            </tr></thead>
            <tbody>{buyers.map((b: any) => (
              <tr key={b.id} style={{ borderBottom: '1px solid #f0ede6' }}>
                <td style={{ padding: 8, fontWeight: 500 }}>{b.first_name} {b.last_name}</td>
                <td style={{ padding: 8, color: '#666' }}>{b.cedula || '—'}</td>
                <td style={{ padding: 8, color: '#666' }}>{b.whatsapp || b.phone || '—'}</td>
                <td style={{ padding: 8, color: '#666' }}>{b.email || '—'}</td>
                <td style={{ padding: 8, color: '#666' }}>{[b.city, b.country].filter(Boolean).join(', ') || '—'}</td>
                <td style={{ padding: 8, whiteSpace: 'nowrap' }}>
                  <button type="button" aria-label="Editar" style={{ ...BTN_LIGHT, padding: '4px 8px' }} onClick={() => { setEditing(b); setOpen(true); }}><Pencil size={12} /></button>{' '}
                  <button type="button" aria-label="Eliminar" style={{ ...BTN_DANGER, padding: '4px 8px' }} onClick={() => remove(b)}><Trash2 size={12} /></button>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {open && <BuyerFormModal buyer={editing} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); setMsg(editing ? 'Comprador actualizado.' : 'Comprador creado.'); load(); }} />}
    </div>
  );
}

// ── Sales ───────────────────────────────────────────────────────────────

function SalesSection({ project, projectId, refreshKey, onChanged }: ScopedProps) {
  const { locale } = useTranslation('construction');
  const { lots } = useProjectLots(projectId, refreshKey);
  const [pipeline, setPipeline] = useState<Record<string, any[]>>({});
  const [totals, setTotals] = useState<Record<string, any>>({});
  const [buyers, setBuyers] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [buyerModal, setBuyerModal] = useState(false);
  const [form, setForm] = useState<any>({ lot_id: '', buyer_id: '', sale_price: '', down_payment: '', status: 'pending', contract_date: today(), notes: '' });
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const currency = project?.currency || 'COP';

  const load = useCallback(() => {
    if (!projectId) return;
    cf(`/projects/${encodeURIComponent(projectId)}/sales/pipeline`)
      .then(d => { setPipeline(d.pipeline && typeof d.pipeline === 'object' ? d.pipeline : {}); setTotals(d.totals || {}); })
      .catch(() => { setPipeline({}); setTotals({}); });
  }, [projectId]);
  const loadBuyers = useCallback(() => { cf('/buyers').then(d => setBuyers(asArray(d.buyers))).catch(() => setBuyers([])); }, []);
  useEffect(() => { load(); }, [load, refreshKey]);
  useEffect(() => { loadBuyers(); }, [loadBuyers]);

  if (!projectId) return <NoProject />;

  const sellable = lots.filter(l => SELLABLE.includes(l.status));
  const openNew = (lotId = '') => {
    const lot = lots.find(l => l.id === lotId);
    setForm({ lot_id: lotId, buyer_id: '', sale_price: lot?.current_price ? String(lot.current_price) : '', down_payment: '', status: 'pending', contract_date: today(), notes: '' });
    setErr(''); setOpen(true);
  };

  const save = async () => {
    const price = num(String(form.sale_price));
    if (!form.lot_id || !form.buyer_id) { setErr('Selecciona el lote y el comprador.'); return; }
    if (!price || price <= 0) { setErr('Indica el valor de la venta.'); return; }
    setBusy(true); setErr('');
    try {
      await cf('/sales', { method: 'POST', body: JSON.stringify({
        lot_id: form.lot_id, buyer_id: form.buyer_id, sale_price: price, currency,
        down_payment: num(String(form.down_payment)) ?? 0, status: form.status,
        contract_date: form.contract_date || null, notes: form.notes || null,
      }) });
      setOpen(false); setMsg('Venta registrada.'); load(); onChanged();
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  const changeStage = async (sale: any, status: string) => {
    setErr(''); setMsg('');
    try { await cf(`/sales/${encodeURIComponent(sale.id)}`, { method: 'PUT', body: JSON.stringify({ status }) }); setMsg(`Venta del lote ${sale.lot_number}: ${SALE_STAGE_ES[status]}.`); load(); onChanged(); }
    catch (e: any) { setErr(e.message); }
  };

  const remove = async (sale: any) => {
    if (!window.confirm(`¿Eliminar la venta del lote ${sale.lot_number}? Se eliminan también sus pagos y el lote vuelve a quedar disponible.`)) return;
    setErr(''); setMsg('');
    try { await cf(`/sales/${encodeURIComponent(sale.id)}`, { method: 'DELETE' }); setMsg('Venta eliminada.'); load(); onChanged(); }
    catch (e: any) { setErr(e.message); }
  };

  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Pipeline de Ventas' : 'Sales Pipeline'} subtitle={project?.name}
        action={<button type="button" style={BTN} onClick={() => openNew()}><Plus size={12} /> Nueva venta</button>} />
      <Notice msg={msg} />{!open ? <Notice msg={err} error /> : null}
      <div className="cf-kanban">
        {SALE_STAGES.map(stage => {
          const cards = asArray(pipeline[stage.key]);
          return (
            <div key={stage.key} style={{ minWidth: 220, flex: '1 0 220px', background: '#f5f3ef', borderRadius: 10, padding: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#555', marginBottom: 2, textTransform: 'uppercase' }}>{locale === 'es' ? stage.label : stage.labelEn}</div>
              <div style={{ fontSize: 10, color: '#999', marginBottom: 8 }}>{cards.length} · {money(totals[stage.key]?.total || 0, currency)}</div>
              {cards.length === 0 ? <div style={{ fontSize: 10, color: '#bbb', textAlign: 'center', padding: 16 }}>Sin ventas</div> : cards.map((s: any) => (
                <div key={s.id} style={{ background: '#fff', borderRadius: 8, padding: 10, marginBottom: 6, border: '1px solid #e5e2dc' }}>
                  <div style={{ fontSize: 12, fontWeight: 600 }}>Lote {s.lot_number}</div>
                  <div style={{ fontSize: 11, color: '#666' }}>{s.buyer_name || `${s.first_name || ''} ${s.last_name || ''}`}</div>
                  <div style={{ fontSize: 11, color: '#b8960c', fontWeight: 600, marginTop: 2 }}>{money(s.sale_price, s.currency || currency)}</div>
                  <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                    <select aria-label="Etapa de la venta" value={s.status} onChange={e => changeStage(s, e.target.value)} style={{ ...INPUT, fontSize: 11, padding: '3px 6px' }}>
                      {SALE_STAGES.map(st => <option key={st.key} value={st.key}>{st.label}</option>)}
                    </select>
                    <button type="button" aria-label="Eliminar venta" style={{ ...BTN_DANGER, padding: '3px 6px' }} onClick={() => remove(s)}><Trash2 size={12} /></button>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {open && (
        <Modal title="Nueva venta" onClose={() => setOpen(false)}>
          <Notice msg={err} error />
          <FormGrid>
            <Field label="Lote *">
              <select aria-label="Lote" style={INPUT} value={form.lot_id} onChange={e => {
                const lot = lots.find(l => l.id === e.target.value);
                setForm({ ...form, lot_id: e.target.value, sale_price: form.sale_price || (lot?.current_price ? String(lot.current_price) : '') });
              }}>
                <option value="">Selecciona un lote</option>
                {sellable.map(l => <option key={l.id} value={l.id}>{l.lot_number} · {LOT_STATUS_ES[l.status]}{l.area_m2 ? ` · ${l.area_m2} m²` : ''}</option>)}
              </select>
            </Field>
            <Field label="Comprador *">
              <div style={{ display: 'flex', gap: 6 }}>
                <select aria-label="Comprador" style={INPUT} value={form.buyer_id} onChange={e => setForm({ ...form, buyer_id: e.target.value })}>
                  <option value="">Selecciona un comprador</option>
                  {buyers.map(b => <option key={b.id} value={b.id}>{b.first_name} {b.last_name}{b.cedula ? ` · ${b.cedula}` : ''}</option>)}
                </select>
                <button type="button" aria-label="Nuevo comprador" title="Nuevo comprador" style={{ ...BTN_LIGHT, padding: '4px 8px' }} onClick={() => setBuyerModal(true)}><Plus size={12} /></button>
              </div>
            </Field>
            <Field label={`Valor de la venta (${currency}) *`}><input aria-label="Valor de la venta" style={INPUT} inputMode="numeric" value={form.sale_price} onChange={e => setForm({ ...form, sale_price: e.target.value })} /></Field>
            <Field label="Cuota inicial"><input style={INPUT} inputMode="numeric" value={form.down_payment} onChange={e => setForm({ ...form, down_payment: e.target.value })} /></Field>
            <Field label="Etapa">
              <select style={INPUT} value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                {SALE_STAGES.filter(s => s.key !== 'cancelled').map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
              </select>
            </Field>
            <Field label="Fecha"><input style={INPUT} type="date" value={form.contract_date} onChange={e => setForm({ ...form, contract_date: e.target.value })} /></Field>
            <Field label="Notas" wide><textarea style={{ ...INPUT, minHeight: 50 }} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
          </FormGrid>
          {sellable.length === 0 ? <div style={{ fontSize: 11, color: '#b45309', marginBottom: 8 }}>No hay lotes disponibles, separados ni en consulta en este proyecto.</div> : null}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" style={BTN_LIGHT} onClick={() => setOpen(false)}>Cancelar</button>
            <button type="button" style={BTN} disabled={busy} onClick={save}>{busy ? 'Guardando…' : 'Registrar venta'}</button>
          </div>
        </Modal>
      )}
      {buyerModal && <BuyerFormModal buyer={null} onClose={() => setBuyerModal(false)} onSaved={(b) => { setBuyerModal(false); loadBuyers(); if (b?.id) setForm((f: any) => ({ ...f, buyer_id: b.id })); }} />}
    </div>
  );
}

// ── Payments ────────────────────────────────────────────────────────────

function PaymentsSection({ project, projectId, refreshKey, onChanged }: ScopedProps) {
  const { locale } = useTranslation('construction');
  const [data, setData] = useState<any>({ payments: [] });
  const [sales, setSales] = useState<any[]>([]);
  const [filter, setFilter] = useState('all');
  const [modal, setModal] = useState<null | { mode: 'new' | 'edit'; payment?: any }>(null);
  const [form, setForm] = useState<any>({});
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const currency = project?.currency || 'COP';

  const load = useCallback(() => {
    if (!projectId) return;
    cf(`/projects/${encodeURIComponent(projectId)}/payments`).then(setData).catch(() => setData({ payments: [] }));
    cf(`/projects/${encodeURIComponent(projectId)}/sales/pipeline`).then(d => {
      const all: any[] = [];
      Object.values(d.pipeline || {}).forEach((list: any) => asArray(list).forEach(s => all.push(s)));
      setSales(all.filter(s => s.status !== 'cancelled'));
    }).catch(() => setSales([]));
  }, [projectId]);
  useEffect(() => { load(); }, [load, refreshKey]);

  if (!projectId) return <NoProject />;

  const payments = asArray(data.payments);
  const visible = payments.filter((p: any) => filter === 'all' || (filter === 'overdue' ? p.is_overdue : p.status === filter));

  const openNew = () => { setForm({ sale_id: sales[0]?.id || '', amount: '', due_date: today(), installment_number: '', status: 'pending', payment_method: 'transferencia', payment_date: '', notes: '' }); setErr(''); setModal({ mode: 'new' }); };
  const openEdit = (p: any) => { setForm({ amount: String(p.amount ?? ''), due_date: p.due_date || '', installment_number: p.installment_number ?? '', status: p.status, payment_method: p.payment_method || '', payment_date: p.payment_date || '', notes: p.notes || '' }); setErr(''); setModal({ mode: 'edit', payment: p }); };

  const save = async () => {
    const amount = num(String(form.amount));
    if (!amount || amount <= 0) { setErr('Indica el valor del pago.'); return; }
    setBusy(true); setErr('');
    try {
      if (modal?.mode === 'edit' && modal.payment) {
        await cf(`/payments/${encodeURIComponent(modal.payment.id)}`, { method: 'PATCH', body: JSON.stringify({
          amount, due_date: form.due_date || null, installment_number: num(String(form.installment_number)), status: form.status,
          payment_method: form.payment_method || null, payment_date: form.payment_date || null, notes: form.notes || null,
        }) });
        setMsg('Pago actualizado.');
      } else {
        const sale = sales.find(s => s.id === form.sale_id);
        if (!sale) { setErr('Selecciona la venta.'); setBusy(false); return; }
        await cf('/payments', { method: 'POST', body: JSON.stringify({
          sale_id: sale.id, buyer_id: sale.buyer_id, amount, currency: sale.currency || currency,
          due_date: form.due_date || null, installment_number: num(String(form.installment_number)), status: form.status,
          payment_method: form.payment_method || null, payment_date: form.status === 'received' ? (form.payment_date || today()) : (form.payment_date || null), notes: form.notes || null,
        }) });
        setMsg('Pago registrado.');
      }
      setModal(null); load(); onChanged();
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  const markReceived = async (p: any) => {
    setErr(''); setMsg('');
    try { await cf(`/payments/${encodeURIComponent(p.id)}`, { method: 'PATCH', body: JSON.stringify({ status: 'received', payment_date: today() }) }); setMsg('Pago marcado como recibido.'); load(); onChanged(); }
    catch (e: any) { setErr(e.message); }
  };
  const remove = async (p: any) => {
    if (!window.confirm('¿Eliminar este pago?')) return;
    try { await cf(`/payments/${encodeURIComponent(p.id)}`, { method: 'DELETE' }); setMsg('Pago eliminado.'); load(); onChanged(); }
    catch (e: any) { setErr(e.message); }
  };

  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Pagos' : 'Payments'} subtitle={project?.name}
        action={<button type="button" style={BTN} onClick={openNew} disabled={sales.length === 0} title={sales.length === 0 ? 'Primero registra una venta' : ''}><Plus size={12} /> Registrar pago</button>} />
      <Notice msg={msg} />{!modal ? <Notice msg={err} error /> : null}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
        <KpiCard label="Recibido" value={money(data.total_received || 0, currency)} color="#16a34a" />
        <KpiCard label="Por cobrar" value={money(data.total_pending || 0, currency)} />
        <KpiCard label="Vencidos" value={data.overdue_count || 0} color="#dc2626" />
      </div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 10, flexWrap: 'wrap' }}>
        {[['all', 'Todos'], ['pending', 'Pendientes'], ['overdue', 'Vencidos'], ['received', 'Recibidos']].map(([k, label]) => (
          <button key={k} type="button" onClick={() => setFilter(k)} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 12, cursor: 'pointer', border: filter === k ? '2px solid #b8960c' : '1px solid #e5e2dc', background: filter === k ? '#fdf8eb' : '#fff' }}>{label}</button>
        ))}
      </div>
      {visible.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{payments.length === 0 ? 'Aún no hay pagos en este proyecto. Los pagos se crean desde una venta o un plan de pagos.' : 'Sin pagos con este filtro.'}</div>
      ) : (
        <div className="cf-table-wrap">
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
              <th style={{ padding: 8 }}>Comprador</th><th style={{ padding: 8 }}>Lote</th><th style={{ padding: 8 }}>Cuota</th><th style={{ padding: 8 }}>Valor</th><th style={{ padding: 8 }}>Vence</th><th style={{ padding: 8 }}>Estado</th><th style={{ padding: 8 }} />
            </tr></thead>
            <tbody>{visible.map((p: any) => (
              <tr key={p.id} style={{ borderBottom: '1px solid #f0ede6' }}>
                <td style={{ padding: 8, fontWeight: 500 }}>{p.buyer_name || '—'}</td>
                <td style={{ padding: 8 }}>{p.lot_number}</td>
                <td style={{ padding: 8 }}>{p.installment_number ?? '—'}</td>
                <td style={{ padding: 8, fontWeight: 600 }}>{money(p.amount, p.currency || currency)}</td>
                <td style={{ padding: 8, color: p.is_overdue ? '#dc2626' : '#666' }}>{p.due_date || '—'}</td>
                <td style={{ padding: 8, color: p.is_overdue ? '#dc2626' : p.status === 'received' ? '#16a34a' : '#666', fontWeight: 600 }}>{p.is_overdue && p.status !== 'received' ? 'Vencido' : (PAYMENT_STATUS_ES[p.status] || p.status)}</td>
                <td style={{ padding: 8, whiteSpace: 'nowrap' }}>
                  {p.status !== 'received' ? <button type="button" style={{ ...BTN, padding: '4px 8px', fontSize: 11 }} onClick={() => markReceived(p)}>Recibido</button> : null}{' '}
                  <button type="button" aria-label="Editar pago" style={{ ...BTN_LIGHT, padding: '4px 8px' }} onClick={() => openEdit(p)}><Pencil size={12} /></button>{' '}
                  <button type="button" aria-label="Eliminar pago" style={{ ...BTN_DANGER, padding: '4px 8px' }} onClick={() => remove(p)}><Trash2 size={12} /></button>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {modal && (
        <Modal title={modal.mode === 'edit' ? 'Editar pago' : 'Registrar pago'} onClose={() => setModal(null)}>
          <Notice msg={err} error />
          <FormGrid>
            {modal.mode === 'new' && (
              <Field label="Venta *" wide>
                <select style={INPUT} value={form.sale_id} onChange={e => setForm({ ...form, sale_id: e.target.value })}>
                  {sales.map(s => <option key={s.id} value={s.id}>Lote {s.lot_number} · {s.buyer_name} · {money(s.sale_price, s.currency || currency)}</option>)}
                </select>
              </Field>
            )}
            <Field label={`Valor (${currency}) *`}><input style={INPUT} inputMode="numeric" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} /></Field>
            <Field label="Cuota #"><input style={INPUT} inputMode="numeric" value={form.installment_number} onChange={e => setForm({ ...form, installment_number: e.target.value })} /></Field>
            <Field label="Fecha de vencimiento"><input style={INPUT} type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })} /></Field>
            <Field label="Estado">
              <select style={INPUT} value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                {Object.entries(PAYMENT_STATUS_ES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </Field>
            <Field label="Medio de pago">
              <select style={INPUT} value={form.payment_method} onChange={e => setForm({ ...form, payment_method: e.target.value })}>
                <option value="">—</option>
                {PAYMENT_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </Field>
            <Field label="Fecha de pago"><input style={INPUT} type="date" value={form.payment_date} onChange={e => setForm({ ...form, payment_date: e.target.value })} /></Field>
            <Field label="Notas" wide><textarea style={{ ...INPUT, minHeight: 50 }} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
          </FormGrid>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" style={BTN_LIGHT} onClick={() => setModal(null)}>Cancelar</button>
            <button type="button" style={BTN} disabled={busy} onClick={save}>{busy ? 'Guardando…' : 'Guardar pago'}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Payment plans (POST /businesses/{slug}/plan-de-pagos) ───────────────

function PaymentPlansSection({ project, projectId, refreshKey, onChanged }: ScopedProps) {
  const { lots } = useProjectLots(projectId, refreshKey);
  const [form, setForm] = useState<any>({ lot_id: '', buyer_name: '', buyer_email: '', buyer_phone: '', amount: '', installments: '12', notes: '' });
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const currency = project?.currency || 'COP';

  if (!projectId || !project) return <NoProject />;
  const sellable = lots.filter(l => SELLABLE.includes(l.status));
  const amount = num(String(form.amount)) ?? 0;
  const installments = Math.max(1, num(String(form.installments)) ?? 1);

  const save = async () => {
    if (!form.lot_id) { setErr('Selecciona el lote.'); return; }
    if (!form.buyer_name.trim()) { setErr('Indica el nombre del comprador.'); return; }
    if (amount <= 0) { setErr('Indica el valor total. No se inventan precios.'); return; }
    setBusy(true); setErr(''); setResult(null);
    const lot = lots.find(l => l.id === form.lot_id);
    try {
      const res = await cf(`${API}/businesses/${encodeURIComponent(project.slug)}/plan-de-pagos`, { method: 'POST', body: JSON.stringify({
        amount, currency, buyer_name: form.buyer_name.trim(), buyer_email: form.buyer_email.trim(), buyer_phone: form.buyer_phone.trim(),
        lot_id: form.lot_id, lot_number: lot?.lot_number, installments, notes: form.notes,
      }) }, true);
      setResult(res);
      setForm({ lot_id: '', buyer_name: '', buyer_email: '', buyer_phone: '', amount: '', installments: '12', notes: '' });
      onChanged();
    } catch (e: any) { setErr(e.message); }
    setBusy(false);
  };

  return (
    <div>
      <SectionHeader title="Planes de pago" subtitle={`${project.name} · crea una separación con sus cuotas (venta pendiente + pagos)`} />
      <Notice msg={err} error />
      {result ? (
        <Notice msg={`Plan creado: ${money(result.sale_price, result.currency || currency)} en ${asArray(result.payments).length || installments} cuota(s). Lo verás en Ventas y Pagos.`} />
      ) : null}
      <div style={{ ...CARD, maxWidth: 640 }}>
        <FormGrid>
          <Field label="Lote *">
            <select aria-label="Lote del plan" style={INPUT} value={form.lot_id} onChange={e => setForm({ ...form, lot_id: e.target.value })}>
              <option value="">Selecciona un lote</option>
              {sellable.map(l => <option key={l.id} value={l.id}>{l.lot_number} · {LOT_STATUS_ES[l.status]}{l.area_m2 ? ` · ${l.area_m2} m²` : ''}</option>)}
            </select>
          </Field>
          <Field label="Comprador *"><input style={INPUT} value={form.buyer_name} onChange={e => setForm({ ...form, buyer_name: e.target.value })} placeholder="Nombre y apellido" /></Field>
          <Field label="Correo"><input style={INPUT} type="email" value={form.buyer_email} onChange={e => setForm({ ...form, buyer_email: e.target.value })} /></Field>
          <Field label="Teléfono / WhatsApp"><input style={INPUT} type="tel" value={form.buyer_phone} onChange={e => setForm({ ...form, buyer_phone: e.target.value })} /></Field>
          <Field label={`Valor total (${currency}) *`}><input style={INPUT} inputMode="numeric" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} /></Field>
          <Field label="Número de cuotas"><input style={INPUT} inputMode="numeric" value={form.installments} onChange={e => setForm({ ...form, installments: e.target.value })} /></Field>
          <Field label="Notas" wide><textarea style={{ ...INPUT, minHeight: 50 }} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></Field>
        </FormGrid>
        {amount > 0 ? <div style={{ fontSize: 12, color: '#555', marginBottom: 10 }}>{installments} cuota(s) de <strong>{money(amount / installments, currency)}</strong></div> : null}
        <button type="button" style={BTN} disabled={busy} onClick={save}>{busy ? 'Creando…' : 'Crear plan de pagos'}</button>
      </div>
    </div>
  );
}

// ── Progress / contractors / materials / infrastructure / reports ───────

function ProgressSection() {
  const { locale } = useTranslation('construction');
  const maxine = useEdition() === 'maxine';
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Avance de Obra' : 'Construction Progress'}
        subtitle={locale === 'es' ? 'Seguimiento por lote y etapa de construcción' : 'Track by lot and construction phase'} />
      {maxine ? <ProjectPhotos /> : (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'Registra el avance desde cada lote en construcción.' : 'Log progress from each lot under construction.'}</div>
      )}
    </div>
  );
}

const EMPTY_CONTRACTOR = { name: '', company: '', specialty: '', phone: '', whatsapp: '', email: '', notes: '' };

function ContractorsSection() {
  const { locale } = useTranslation('construction');
  const [contractors, setContractors] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<any>(EMPTY_CONTRACTOR);
  const [err, setErr] = useState('');
  const load = useCallback(() => { cf('/contractors').then(d => setContractors(asArray(d.contractors ?? d))).catch(() => setContractors([])); }, []);
  useEffect(() => { load(); }, [load]);
  const save = async () => {
    if (!form.name.trim()) { setErr('El nombre es obligatorio.'); return; }
    try { await cf('/contractors', { method: 'POST', body: JSON.stringify(form) }); setOpen(false); load(); }
    catch (e: any) { setErr(e.message); }
  };
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Contratistas' : 'Contractors'}
        action={<button type="button" style={BTN} onClick={() => { setForm(EMPTY_CONTRACTOR); setErr(''); setOpen(true); }}><Plus size={12} /> {locale === 'es' ? 'Nuevo' : 'New'}</button>} />
      {contractors.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'No hay contratistas registrados.' : 'No contractors registered.'}</div> : (
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }}>
          {contractors.map((c: any) => (
            <div key={c.id} style={{ ...CARD, padding: 14 }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{c.name}</div>
              <div style={{ fontSize: 11, color: '#888' }}>{c.specialty} {c.company ? `• ${c.company}` : ''}</div>
              <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>{c.phone || c.whatsapp || '—'}</div>
              {c.rating > 0 && <div style={{ fontSize: 11, color: '#b8960c', marginTop: 2 }}>{'★'.repeat(Math.round(c.rating))} {Number(c.rating).toFixed(1)}</div>}
            </div>
          ))}
        </div>
      )}
      {open && (
        <Modal title="Nuevo contratista" onClose={() => setOpen(false)}>
          <Notice msg={err} error />
          <FormGrid>
            <Field label="Nombre *"><input style={INPUT} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Empresa"><input style={INPUT} value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} /></Field>
            <Field label="Especialidad"><input style={INPUT} value={form.specialty} onChange={e => setForm({ ...form, specialty: e.target.value })} placeholder="Vías, redes, mampostería…" /></Field>
            <Field label="Teléfono"><input style={INPUT} type="tel" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="WhatsApp"><input style={INPUT} type="tel" value={form.whatsapp} onChange={e => setForm({ ...form, whatsapp: e.target.value })} /></Field>
            <Field label="Correo"><input style={INPUT} type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></Field>
          </FormGrid>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" style={BTN_LIGHT} onClick={() => setOpen(false)}>Cancelar</button>
            <button type="button" style={BTN} onClick={save}>Guardar</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

const EMPTY_MATERIAL = { name: '', category: '', unit: '', unit_cost: '', supplier: '', stock_on_site: '', reorder_point: '' };

function MaterialsSection({ project, projectId, refreshKey }: ScopedProps) {
  const { locale } = useTranslation('construction');
  const [materials, setMaterials] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<any>(EMPTY_MATERIAL);
  const [err, setErr] = useState('');
  const load = useCallback(() => {
    if (!projectId) return;
    cf(`/projects/${encodeURIComponent(projectId)}/materials`).then(d => setMaterials(asArray(d.materials ?? d))).catch(() => setMaterials([]));
  }, [projectId]);
  useEffect(() => { load(); }, [load, refreshKey]);
  if (!projectId) return <NoProject />;
  const save = async () => {
    if (!form.name.trim()) { setErr('El nombre es obligatorio.'); return; }
    try {
      await cf(`/materials?project_id=${encodeURIComponent(projectId)}`, { method: 'POST', body: JSON.stringify({
        name: form.name.trim(), category: form.category || null, unit: form.unit || null, supplier: form.supplier || null,
        unit_cost: num(String(form.unit_cost)) ?? 0, stock_on_site: num(String(form.stock_on_site)) ?? 0, reorder_point: num(String(form.reorder_point)) ?? 0,
      }) });
      setOpen(false); load();
    } catch (e: any) { setErr(e.message); }
  };
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Materiales' : 'Materials'} subtitle={project?.name}
        action={<button type="button" style={BTN} onClick={() => { setForm(EMPTY_MATERIAL); setErr(''); setOpen(true); }}><Plus size={12} /> {locale === 'es' ? 'Nuevo Material' : 'New Material'}</button>} />
      {materials.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'No hay materiales registrados.' : 'No materials registered.'}</div> : (
        <div className="cf-table-wrap">
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
              <th style={{ padding: 8 }}>Material</th><th style={{ padding: 8 }}>Categoría</th><th style={{ padding: 8 }}>Unidad</th><th style={{ padding: 8 }}>Costo</th><th style={{ padding: 8 }}>Stock</th>
            </tr></thead>
            <tbody>{materials.map((m: any) => (
              <tr key={m.id} style={{ borderBottom: '1px solid #f0ede6' }}>
                <td style={{ padding: 8, fontWeight: 500 }}>{m.name}</td>
                <td style={{ padding: 8, color: '#666' }}>{m.category}</td>
                <td style={{ padding: 8, color: '#666' }}>{m.unit}</td>
                <td style={{ padding: 8 }}>{money(m.unit_cost, project?.currency || 'COP')}</td>
                <td style={{ padding: 8, fontWeight: 600, color: m.stock_on_site <= m.reorder_point ? '#dc2626' : '#16a34a' }}>{m.stock_on_site}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {open && (
        <Modal title="Nuevo material" onClose={() => setOpen(false)}>
          <Notice msg={err} error />
          <FormGrid>
            <Field label="Nombre *"><input style={INPUT} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Categoría"><input style={INPUT} value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} /></Field>
            <Field label="Unidad"><input style={INPUT} value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} placeholder="bulto, m³, und…" /></Field>
            <Field label="Costo unitario"><input style={INPUT} inputMode="numeric" value={form.unit_cost} onChange={e => setForm({ ...form, unit_cost: e.target.value })} /></Field>
            <Field label="Proveedor"><input style={INPUT} value={form.supplier} onChange={e => setForm({ ...form, supplier: e.target.value })} /></Field>
            <Field label="Stock en obra"><input style={INPUT} inputMode="decimal" value={form.stock_on_site} onChange={e => setForm({ ...form, stock_on_site: e.target.value })} /></Field>
            <Field label="Punto de reorden"><input style={INPUT} inputMode="decimal" value={form.reorder_point} onChange={e => setForm({ ...form, reorder_point: e.target.value })} /></Field>
          </FormGrid>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" style={BTN_LIGHT} onClick={() => setOpen(false)}>Cancelar</button>
            <button type="button" style={BTN} onClick={save}>Guardar</button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function InfraSection() {
  const { locale } = useTranslation('construction');
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Infraestructura' : 'Infrastructure'}
        subtitle={locale === 'es' ? 'Vías, acueducto, alcantarillado, energía, gas, internet' : 'Roads, water, sewer, power, gas, internet'} />
      <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'Aún no hay obras de infraestructura registradas.' : 'No infrastructure works yet.'}</div>
    </div>
  );
}

function ReportsSection() {
  const { locale } = useTranslation('construction');
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Reportes' : 'Reports'} />
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
        {[
          { label: locale === 'es' ? 'Resumen Ejecutivo' : 'Executive Summary', icon: BarChart3, desc: locale === 'es' ? 'Unidades vendidas, ingresos, avance' : 'Units sold, revenue, progress' },
          { label: locale === 'es' ? 'Reporte Financiero' : 'Financial Report', icon: DollarSign, desc: locale === 'es' ? 'Presupuesto vs real, flujo de caja' : 'Budget vs actual, cash flow' },
          { label: locale === 'es' ? 'Avance de Obra' : 'Construction Progress', icon: Hammer, desc: locale === 'es' ? 'Progreso por lote y etapa' : 'Progress by lot and phase' },
        ].map((r, i) => (
          <div key={i} style={{ ...CARD }}>
            <r.icon size={20} style={{ color: '#b8960c', marginBottom: 8 }} />
            <div style={{ fontSize: 13, fontWeight: 600 }}>{r.label}</div>
            <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>{r.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
