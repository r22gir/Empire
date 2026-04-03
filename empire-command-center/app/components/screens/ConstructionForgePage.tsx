'use client';
import React, { useState, useEffect, Suspense, lazy } from 'react';
import { API } from '../../lib/api';
import { useTranslation } from '../../lib/i18n';
import {
  Building2, Map, Users, DollarSign, Hammer, HardHat, Package,
  Network, BarChart3, Loader2, Plus, Search, ChevronRight,
  TrendingUp, MapPin, Calendar, AlertTriangle, CheckCircle,
  Clock, Eye, ChevronDown, ChevronUp, Filter
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';

const CF_API = `${API}/construction`;

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Tablero', labelEn: 'Dashboard', icon: BarChart3 },
  { id: 'projects', label: 'Proyectos', labelEn: 'Projects', icon: Building2 },
  { id: 'lotmap', label: 'Mapa de Lotes', labelEn: 'Lot Map', icon: Map },
  { id: 'buyers', label: 'Compradores', labelEn: 'Buyers', icon: Users },
  { id: 'sales', label: 'Ventas', labelEn: 'Sales', icon: DollarSign },
  { id: 'payments', label: 'Pagos', labelEn: 'Payments', icon: DollarSign },
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
  sold: '#2563eb',
  under_construction: '#8b5cf6',
  delivered: '#6b7280',
  hold: '#dc2626',
};

interface CfProject { id: number; name: string; slug: string; location: string; total_lots: number; status: string; currency: string; }

interface CfLot { id: number; lot_number: string; block: string; area_m2: number; current_price: number; status: string; phase_id: number; }

interface ConstructionForgePageProps { initialSection?: string; }

export default function ConstructionForgePage({ initialSection }: ConstructionForgePageProps) {
  const [section, setSection] = useState<Section>((initialSection as Section) || 'dashboard');
  const { t, locale } = useTranslation('construction');

  useEffect(() => {
    if (initialSection) setSection(initialSection as Section);
  }, [initialSection]);

  const navLabel = (nav: typeof NAV_SECTIONS[number]) => locale === 'es' ? nav.label : nav.labelEn;

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection />;
      case 'projects': return <ProjectsSection />;
      case 'lotmap': return <LotMapSection />;
      case 'buyers': return <BuyersSection />;
      case 'sales': return <SalesSection />;
      case 'payments': return <PaymentsSection />;
      case 'construction': return <ProgressSection />;
      case 'contractors': return <ContractorsSection />;
      case 'materials': return <MaterialsSection />;
      case 'infrastructure': return <InfraSection />;
      case 'reports': return <ReportsSection />;
      case 'docs': return <ProductDocs product="construction" />;
      default: return <DashboardSection />;
    }
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: '#faf9f7' }}>
      {/* Sidebar */}
      <div style={{ width: 200, borderRight: '1px solid #e5e2dc', padding: '16px 0', flexShrink: 0, overflowY: 'auto' }}>
        <div style={{ padding: '0 16px 12px', borderBottom: '1px solid #e5e2dc', marginBottom: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#b8960c', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Building2 size={16} /> ConstructionForge
          </div>
          <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>
            {locale === 'es' ? 'Gestión de Desarrollo Inmobiliario' : 'Real Estate Development'}
          </div>
        </div>
        {NAV_SECTIONS.map(nav => (
          <button key={nav.id} onClick={() => setSection(nav.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8, width: '100%',
              padding: '8px 16px', border: 'none', cursor: 'pointer',
              background: section === nav.id ? '#f0ede6' : 'transparent',
              color: section === nav.id ? '#b8960c' : '#666',
              fontWeight: section === nav.id ? 600 : 400, fontSize: 12, textAlign: 'left',
            }}>
            <nav.icon size={14} />
            {navLabel(nav)}
          </button>
        ))}
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
        {renderContent()}
      </div>
    </div>
  );
}

// === SECTION COMPONENTS ===

function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
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

function KpiCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '16px 18px', flex: 1, minWidth: 140 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || '#1a1a1a', marginTop: 4 }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function DashboardSection() {
  const { locale } = useTranslation('construction');
  const [project, setProject] = useState<CfProject | null>(null);
  const [dashboard, setDashboard] = useState<any>(null);
  const [projects, setProjects] = useState<CfProject[]>([]);

  useEffect(() => {
    fetch(`${CF_API}/projects`).then(r => r.json()).then(data => {
      const list = data.projects || data || [];
      setProjects(list);
      if (list.length > 0) setProject(list[0]);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (project) {
      fetch(`${CF_API}/projects/${project.id}/dashboard`).then(r => r.json()).then(setDashboard).catch(() => {});
    }
  }, [project]);

  const d = dashboard || {};
  const fmt = (n: number) => project?.currency === 'COP'
    ? `$${(n || 0).toLocaleString('es-CO')} COP`
    : `$${(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;

  return (
    <div>
      <SectionHeader
        title={locale === 'es' ? 'Tablero Ejecutivo' : 'Executive Dashboard'}
        subtitle={project?.name || ''}
        action={projects.length > 1 ? (
          <select value={project?.id || ''} onChange={e => setProject(projects.find(p => p.id === Number(e.target.value)) || null)}
            style={{ fontSize: 12, padding: '6px 10px', borderRadius: 6, border: '1px solid #e5e2dc' }}>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        ) : undefined}
      />
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <KpiCard label={locale === 'es' ? 'Lotes Disponibles' : 'Available Lots'} value={d.available_lots ?? '—'} color="#16a34a" />
        <KpiCard label={locale === 'es' ? 'Lotes Vendidos' : 'Lots Sold'} value={d.sold_lots ?? '—'} color="#2563eb" />
        <KpiCard label={locale === 'es' ? 'Ingresos Recaudados' : 'Revenue Collected'} value={fmt(d.revenue_collected || 0)} color="#b8960c" />
        <KpiCard label={locale === 'es' ? 'Ingresos Pendientes' : 'Revenue Pending'} value={fmt(d.revenue_pending || 0)} />
        <KpiCard label={locale === 'es' ? 'Avance de Obra' : 'Construction Progress'} value={`${d.construction_progress ?? 0}%`} color="#8b5cf6" />
      </div>

      {/* Mini lot map */}
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, marginBottom: 16 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>{locale === 'es' ? 'Estado de Lotes' : 'Lot Status'}</h3>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {(d.lots || []).slice(0, 60).map((lot: any, i: number) => (
            <div key={i} style={{
              width: 28, height: 28, borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 8, fontWeight: 600, color: '#fff', cursor: 'pointer',
              background: LOT_STATUS_COLORS[lot.status] || '#999',
            }} title={`${lot.lot_number} — ${lot.status}`}>
              {lot.lot_number?.replace('L-', '')}
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 12, marginTop: 10, fontSize: 10 }}>
          {Object.entries(LOT_STATUS_COLORS).map(([status, color]) => (
            <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: color }} />
              {locale === 'es' ? {
                available: 'Disponible', reserved: 'Separado', sold: 'Vendido',
                under_construction: 'En Construcción', delivered: 'Entregado', hold: 'Retenido'
              }[status] : status.replace('_', ' ')}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ProjectsSection() {
  const { locale } = useTranslation('construction');
  const [projects, setProjects] = useState<CfProject[]>([]);
  useEffect(() => {
    fetch(`${CF_API}/projects`).then(r => r.json()).then(d => setProjects(d.projects || d || [])).catch(() => {});
  }, []);
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Proyectos' : 'Projects'}
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#b8960c', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> {locale === 'es' ? 'Nuevo Proyecto' : 'New Project'}</button>} />
      {projects.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'No hay proyectos. Crea el primero.' : 'No projects. Create the first one.'}</div>
      ) : projects.map(p => (
        <div key={p.id} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>{p.name}</div>
              <div style={{ fontSize: 11, color: '#888', display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                <MapPin size={10} /> {p.location}
              </div>
            </div>
            <div style={{ padding: '4px 10px', borderRadius: 12, fontSize: 10, fontWeight: 600, background: '#f0ede6', color: '#b8960c' }}>
              {p.status}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: '#666' }}>
            <span>{p.total_lots} {locale === 'es' ? 'lotes' : 'lots'}</span>
            <span>{p.currency}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function LotMapSection() {
  const { locale } = useTranslation('construction');
  const [lots, setLots] = useState<CfLot[]>([]);
  const [selected, setSelected] = useState<CfLot | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    fetch(`${CF_API}/projects/1/lots`).then(r => r.json()).then(d => setLots(d.lots || d || [])).catch(() => {});
  }, []);

  const filtered = filter === 'all' ? lots : lots.filter(l => l.status === filter);

  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Mapa de Lotes' : 'Lot Map'} />
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {['all', 'available', 'reserved', 'sold', 'under_construction', 'delivered', 'hold'].map(s => (
          <button key={s} onClick={() => setFilter(s)} style={{
            fontSize: 11, padding: '5px 12px', borderRadius: 14, border: filter === s ? '2px solid #b8960c' : '1px solid #e5e2dc',
            background: filter === s ? '#fdf8eb' : '#fff', cursor: 'pointer', fontWeight: filter === s ? 600 : 400,
            color: filter === s ? '#b8960c' : '#666',
          }}>
            {s === 'all' ? (locale === 'es' ? 'Todos' : 'All') :
             locale === 'es' ? { available: 'Disponible', reserved: 'Separado', sold: 'Vendido', under_construction: 'En Construcción', delivered: 'Entregado', hold: 'Retenido' }[s] : s.replace('_', ' ')
            } ({s === 'all' ? lots.length : lots.filter(l => l.status === s).length})
          </button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(52px, 1fr))', gap: 6, flex: 1 }}>
          {filtered.map(lot => (
            <div key={lot.id} onClick={() => setSelected(lot)} style={{
              padding: 8, borderRadius: 6, textAlign: 'center', cursor: 'pointer', fontSize: 10, fontWeight: 600,
              color: '#fff', background: LOT_STATUS_COLORS[lot.status] || '#999',
              border: selected?.id === lot.id ? '3px solid #b8960c' : '2px solid transparent',
              transition: 'all 0.15s',
            }}>
              {lot.lot_number}
              <div style={{ fontSize: 8, opacity: 0.8 }}>{lot.area_m2}m²</div>
            </div>
          ))}
        </div>
        {selected && (
          <div style={{ width: 260, background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, flexShrink: 0 }}>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{locale === 'es' ? 'Lote' : 'Lot'} {selected.lot_number}</h4>
            <div style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div><span style={{ color: '#888' }}>{locale === 'es' ? 'Área' : 'Area'}:</span> {selected.area_m2} m²</div>
              <div><span style={{ color: '#888' }}>{locale === 'es' ? 'Manzana' : 'Block'}:</span> {selected.block || '—'}</div>
              <div><span style={{ color: '#888' }}>{locale === 'es' ? 'Precio' : 'Price'}:</span> ${(selected.current_price || 0).toLocaleString()}</div>
              <div>
                <span style={{ color: '#888' }}>{locale === 'es' ? 'Estado' : 'Status'}:</span>{' '}
                <span style={{ fontWeight: 600, color: LOT_STATUS_COLORS[selected.status] }}>
                  {locale === 'es' ? { available: 'Disponible', reserved: 'Separado', sold: 'Vendido', under_construction: 'En Construcción', delivered: 'Entregado', hold: 'Retenido' }[selected.status] : selected.status}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function BuyersSection() {
  const { locale } = useTranslation('construction');
  const [buyers, setBuyers] = useState<any[]>([]);
  useEffect(() => { fetch(`${CF_API}/buyers`).then(r => r.json()).then(d => setBuyers(d.buyers || d || [])).catch(() => {}); }, []);
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Compradores' : 'Buyers'}
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#b8960c', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> {locale === 'es' ? 'Nuevo Comprador' : 'New Buyer'}</button>} />
      {buyers.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'No hay compradores registrados.' : 'No buyers registered.'}</div> : (
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Nombre' : 'Name'}</th>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Cédula' : 'ID'}</th>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Teléfono' : 'Phone'}</th>
            <th style={{ padding: 8 }}>Email</th>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Ciudad' : 'City'}</th>
          </tr></thead>
          <tbody>{buyers.map(b => (
            <tr key={b.id} style={{ borderBottom: '1px solid #f0ede6' }}>
              <td style={{ padding: 8, fontWeight: 500 }}>{b.first_name} {b.last_name}</td>
              <td style={{ padding: 8, color: '#666' }}>{b.cedula || '—'}</td>
              <td style={{ padding: 8, color: '#666' }}>{b.phone || b.whatsapp || '—'}</td>
              <td style={{ padding: 8, color: '#666' }}>{b.email || '—'}</td>
              <td style={{ padding: 8, color: '#666' }}>{b.city || '—'}</td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}

function SalesSection() {
  const { locale } = useTranslation('construction');
  const STAGES = locale === 'es'
    ? ['Prospecto', 'Visita', 'Separación', 'Promesa', 'Escritura', 'Entregado']
    : ['Prospect', 'Visit', 'Reservation', 'Contract', 'Deed', 'Delivered'];
  const stageKeys = ['prospecto', 'visita', 'separacion', 'promesa', 'escritura', 'entregado'];

  const [pipeline, setPipeline] = useState<Record<string, any[]>>({});
  useEffect(() => {
    fetch(`${CF_API}/projects/1/sales/pipeline`).then(r => r.json()).then(d => setPipeline(d.pipeline || {})).catch(() => {});
  }, []);

  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Pipeline de Ventas' : 'Sales Pipeline'} />
      <div style={{ display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 12 }}>
        {STAGES.map((stage, i) => {
          const cards = pipeline[stageKeys[i]] || [];
          return (
            <div key={i} style={{ minWidth: 200, background: '#f5f3ef', borderRadius: 10, padding: 10, flex: 1 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#b8960c', marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                {stage} <span style={{ color: '#999' }}>{cards.length}</span>
              </div>
              {cards.length === 0 ? (
                <div style={{ fontSize: 10, color: '#ccc', textAlign: 'center', padding: 16 }}>—</div>
              ) : cards.map((card: any, j: number) => (
                <div key={j} style={{ background: '#fff', borderRadius: 8, padding: 10, marginBottom: 6, border: '1px solid #e5e2dc', fontSize: 11 }}>
                  <div style={{ fontWeight: 600 }}>{card.buyer_name || 'Buyer'}</div>
                  <div style={{ color: '#888', fontSize: 10 }}>{card.lot_number} — ${(card.sale_price || 0).toLocaleString()}</div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PaymentsSection() {
  const { locale } = useTranslation('construction');
  const [payments, setPayments] = useState<any[]>([]);
  useEffect(() => { fetch(`${CF_API}/projects/1/payments/overdue`).then(r => r.json()).then(d => setPayments(d.payments || d || [])).catch(() => {}); }, []);
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Control de Pagos' : 'Payment Tracker'} />
      {payments.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'No hay pagos vencidos.' : 'No overdue payments.'}</div> : (
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Comprador' : 'Buyer'}</th>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Monto' : 'Amount'}</th>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Vencimiento' : 'Due Date'}</th>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Estado' : 'Status'}</th>
          </tr></thead>
          <tbody>{payments.map((p: any) => (
            <tr key={p.id} style={{ borderBottom: '1px solid #f0ede6' }}>
              <td style={{ padding: 8 }}>{p.buyer_name || '—'}</td>
              <td style={{ padding: 8, fontWeight: 600 }}>${(p.amount || 0).toLocaleString()}</td>
              <td style={{ padding: 8, color: '#dc2626' }}>{p.due_date}</td>
              <td style={{ padding: 8 }}><span style={{ padding: '2px 8px', borderRadius: 8, fontSize: 10, fontWeight: 600, background: p.status === 'overdue' ? '#fef2f2' : '#f0fdf4', color: p.status === 'overdue' ? '#dc2626' : '#16a34a' }}>{p.status}</span></td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}

function ProgressSection() {
  const { locale } = useTranslation('construction');
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Avance de Obra' : 'Construction Progress'}
        subtitle={locale === 'es' ? 'Seguimiento por lote y etapa de construcción' : 'Track by lot and construction phase'} />
      <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'Selecciona un proyecto para ver el avance.' : 'Select a project to see progress.'}</div>
    </div>
  );
}

function ContractorsSection() {
  const { locale } = useTranslation('construction');
  const [contractors, setContractors] = useState<any[]>([]);
  useEffect(() => { fetch(`${CF_API}/contractors`).then(r => r.json()).then(d => setContractors(d.contractors || d || [])).catch(() => {}); }, []);
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Contratistas' : 'Contractors'}
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#b8960c', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> {locale === 'es' ? 'Nuevo' : 'New'}</button>} />
      {contractors.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'No hay contratistas registrados.' : 'No contractors registered.'}</div> : (
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))' }}>
          {contractors.map((c: any) => (
            <div key={c.id} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 14 }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{c.name}</div>
              <div style={{ fontSize: 11, color: '#888' }}>{c.specialty} {c.company ? `• ${c.company}` : ''}</div>
              <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>{c.phone || c.whatsapp || '—'}</div>
              {c.rating > 0 && <div style={{ fontSize: 11, color: '#b8960c', marginTop: 2 }}>{'★'.repeat(Math.round(c.rating))} {c.rating.toFixed(1)}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MaterialsSection() {
  const { locale } = useTranslation('construction');
  const [materials, setMaterials] = useState<any[]>([]);
  useEffect(() => { fetch(`${CF_API}/projects/1/materials`).then(r => r.json()).then(d => setMaterials(d.materials || d || [])).catch(() => {}); }, []);
  return (
    <div>
      <SectionHeader title={locale === 'es' ? 'Materiales' : 'Materials'}
        action={<button style={{ fontSize: 12, padding: '6px 14px', background: '#b8960c', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}><Plus size={12} /> {locale === 'es' ? 'Nuevo Material' : 'New Material'}</button>} />
      {materials.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'No hay materiales registrados.' : 'No materials registered.'}</div> : (
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Material' : 'Material'}</th>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Categoría' : 'Category'}</th>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Unidad' : 'Unit'}</th>
            <th style={{ padding: 8 }}>{locale === 'es' ? 'Costo' : 'Cost'}</th>
            <th style={{ padding: 8 }}>Stock</th>
          </tr></thead>
          <tbody>{materials.map((m: any) => (
            <tr key={m.id} style={{ borderBottom: '1px solid #f0ede6' }}>
              <td style={{ padding: 8, fontWeight: 500 }}>{m.name}</td>
              <td style={{ padding: 8, color: '#666' }}>{m.category}</td>
              <td style={{ padding: 8, color: '#666' }}>{m.unit}</td>
              <td style={{ padding: 8 }}>${(m.unit_cost || 0).toLocaleString()}</td>
              <td style={{ padding: 8, fontWeight: 600, color: m.stock_on_site <= m.reorder_point ? '#dc2626' : '#16a34a' }}>{m.stock_on_site}</td>
            </tr>
          ))}</tbody>
        </table>
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
      <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>{locale === 'es' ? 'Selecciona un proyecto para ver la infraestructura.' : 'Select a project to see infrastructure.'}</div>
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
          { label: locale === 'es' ? 'Reporte de Ventas' : 'Sales Report', icon: TrendingUp, desc: locale === 'es' ? 'Velocidad de ventas, conversión' : 'Sales velocity, conversion' },
          { label: locale === 'es' ? 'Avance de Obra' : 'Construction Progress', icon: Hammer, desc: locale === 'es' ? 'Progreso por lote y etapa' : 'Progress by lot and phase' },
        ].map((r, i) => (
          <div key={i} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, cursor: 'pointer' }}>
            <r.icon size={20} style={{ color: '#b8960c', marginBottom: 8 }} />
            <div style={{ fontSize: 13, fontWeight: 600 }}>{r.label}</div>
            <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>{r.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
