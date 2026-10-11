'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  INSTAGRAM_URL,
  PUBLIC_API,
  STATUS_LABEL,
  STATUS_ORDER,
  formatCOP,
  formatM2,
  whatsappHref,
  type LotStatus,
  type PublicLot,
  type PublicProject,
} from '../ventasShared';

const GALLERY_SLOTS = ['Fachada', 'Sala y comedor', 'Cocina', 'Habitación', 'Zonas comunes', 'Entorno'];
const REFRESH_MS = 30000;

type FormState = 'idle' | 'sending' | 'ok' | 'error';

export default function VentasProject() {
  const params = useParams<{ slug: string }>();
  const slug = String(params?.slug || '');
  const [project, setProject] = useState<PublicProject | null>(null);
  const [lots, setLots] = useState<PublicLot[]>([]);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [filter, setFilter] = useState<LotStatus | 'all'>('all');
  const [selected, setSelected] = useState<PublicLot | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [form, setForm] = useState({ name: '', phone: '', email: '', city: '', lot: '', message: '', consent: false, website: '' });
  const [formState, setFormState] = useState<FormState>('idle');
  const [formMsg, setFormMsg] = useState('');
  const formRef = useRef<HTMLElement | null>(null);

  const loadSitemap = useCallback(async () => {
    try {
      const r = await fetch(`${PUBLIC_API}/projects/${encodeURIComponent(slug)}/sitemap`, { cache: 'no-store' });
      if (!r.ok) return;
      const d = await r.json();
      setLots(d.lots || []);
      setUpdatedAt(new Date());
      setSelected((cur) => (cur ? (d.lots || []).find((l: PublicLot) => l.number === cur.number && l.block === cur.block) || null : cur));
    } catch {
      /* keep the last map */
    }
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    let alive = true;
    fetch(`${PUBLIC_API}/projects/${encodeURIComponent(slug)}`, { cache: 'no-store' })
      .then(async (r) => {
        if (r.status === 404) { if (alive) setNotFound(true); return; }
        if (!r.ok) throw new Error(String(r.status));
        const d = await r.json();
        if (alive) setProject(d.project);
      })
      .catch(() => alive && setLoadError(true));
    loadSitemap();
    const timer = window.setInterval(loadSitemap, REFRESH_MS);
    return () => { alive = false; window.clearInterval(timer); };
  }, [slug, loadSitemap]);

  useEffect(() => {
    if (project) document.title = `${project.name} — Proyectos en venta`;
  }, [project]);

  const unit = project?.unit_label || 'Lote';
  const counts = useMemo(() => {
    const c: Record<LotStatus, number> = { available: 0, reserved: 0, sold: 0, consultar: 0 };
    lots.forEach((l) => { c[l.status] = (c[l.status] || 0) + 1; });
    return c;
  }, [lots]);
  const blocks = useMemo(() => {
    const groups = new Map<string, PublicLot[]>();
    lots.forEach((l) => {
      const key = l.block ? `Manzana ${l.block}` : (l.phase || '');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(l);
    });
    return Array.from(groups.entries());
  }, [lots]);

  const interested = (lot: PublicLot) => {
    setForm((f) => ({ ...f, lot: lot.number }));
    setSelected(null);
    window.setTimeout(() => formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formState === 'sending') return;
    setFormState('sending');
    setFormMsg('');
    try {
      const r = await fetch(`${PUBLIC_API}/projects/${encodeURIComponent(slug)}/lead`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, email: form.email || null, city: form.city || null, lot: form.lot || null, message: form.message || null }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        const detail = typeof d?.detail === 'string' ? d.detail : 'Revisa los datos e intenta de nuevo.';
        setFormState('error');
        setFormMsg(r.status === 429 ? detail : r.status === 422 && typeof d?.detail !== 'string' ? 'Revisa los datos: nombre y teléfono son obligatorios.' : detail);
        return;
      }
      setFormState('ok');
      setFormMsg(d?.message || '¡Gracias! Un asesor te contactará pronto.');
      setForm({ name: '', phone: '', email: '', city: '', lot: '', message: '', consent: false, website: '' });
    } catch {
      setFormState('error');
      setFormMsg('No pudimos enviar tus datos. Revisa tu conexión e intenta de nuevo.');
    }
  };

  if (notFound) {
    return (
      <div className="gv-wrap">
        <Link href="/ventas" className="gv-back">← Todos los proyectos</Link>
        <h1 className="gv-h1">Proyecto no encontrado</h1>
        <p className="gv-lead">Este proyecto no está publicado. Mira los demás proyectos disponibles.</p>
      </div>
    );
  }

  const waText = project ? `Hola, me interesa el proyecto ${project.name}${form.lot ? ` (${unit.toLowerCase()} ${form.lot})` : ''}. ¿Me pueden dar información?` : '';

  return (
    <div className="gv-wrap" data-project-page={slug}>
      <Link href="/ventas" className="gv-back">← Todos los proyectos</Link>
      {loadError && <p className="gv-msg gv-msg-err">No pudimos cargar el proyecto. Intenta de nuevo en un momento.</p>}
      {!project && !loadError && <p className="gv-muted">Cargando proyecto…</p>}
      {project && (
        <>
          <div className="gv-hero">
            <div className="gv-ph" role="img" aria-label={`Foto principal pendiente de ${project.name}`}>
              <span className="gv-ph-tag">Foto pendiente</span>
              <span>{project.name}<small>Espacio reservado para la foto principal</small></span>
            </div>
          </div>
          <div className="gv-row" style={{ marginTop: 14 }}>
            <span className="gv-chip">{project.status}</span>
            {counts.available > 0 && <span className="gv-chip gv-chip-acc">{counts.available} disponibles</span>}
          </div>
          <h1 className="gv-h1">{project.name}</h1>
          {project.tagline && <p className="gv-lead" style={{ fontWeight: 700 }}>{project.tagline}</p>}
          {project.location && <p className="gv-muted">📍 {project.location}</p>}
          {project.description && <p className="gv-lead">{project.description}</p>}
          {project.highlights.length > 0 && (
            <ul className="gv-hl">{project.highlights.map((h) => <li key={h}>{h}</li>)}</ul>
          )}
          {project.price_note && <p className="gv-lead" style={{ fontWeight: 900, color: '#208D63' }}>{project.price_note}</p>}
          <div className="gv-row" style={{ marginTop: 14 }}>
            <button type="button" className="gv-btn gv-btn-primary" onClick={() => formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>
              Quiero información
            </button>
            {project.whatsapp && (
              <a className="gv-btn gv-btn-wa" href={whatsappHref(project.whatsapp, waText)} target="_blank" rel="noopener noreferrer">
                WhatsApp
              </a>
            )}
          </div>
        </>
      )}

      <section className="gv-section" id="mapa" aria-labelledby="gv-map-title">
        <h2 className="gv-h2" id="gv-map-title">Mapa de {unit === 'Lote' ? 'lotes' : 'unidades'}</h2>
        <p className="gv-muted" style={{ marginTop: -6 }}>
          Plano esquemático, no a escala. Toca un {unit.toLowerCase()} para ver el detalle.
          {updatedAt && <> Actualizado {updatedAt.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}.</>}
        </p>
        <div className="gv-filter" role="group" aria-label="Filtrar por estado">
          <button type="button" aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>Todos ({lots.length})</button>
          {STATUS_ORDER.map((s) => (
            <button key={s} type="button" aria-pressed={filter === s} onClick={() => setFilter(s)}>
              <span className={`gv-dot gv-s-${s}`} />{STATUS_LABEL[s]} ({counts[s]})
            </button>
          ))}
        </div>
        {lots.length === 0 && <p className="gv-muted">Pronto publicaremos el mapa.</p>}
        {blocks.map(([label, group]) => (
          <div key={label || 'all'} style={{ marginBottom: 12 }}>
            {label && blocks.length > 1 && <p className="gv-muted" style={{ fontWeight: 700, margin: '4px 0 8px' }}>{label}</p>}
            <div className="gv-map" data-lot-map>
              {group.map((lot) => {
                const dim = filter !== 'all' && lot.status !== filter;
                return (
                  <button
                    key={`${lot.block || ''}-${lot.number}`}
                    type="button"
                    className={`gv-lot gv-s-${lot.status}`}
                    data-status={lot.status}
                    aria-pressed={selected?.number === lot.number && selected?.block === lot.block}
                    aria-label={`${unit} ${lot.number}: ${lot.status_label}`}
                    style={{ opacity: dim ? 0.25 : 1 }}
                    onClick={() => setSelected(lot)}
                  >
                    {lot.number}
                    <small>{lot.status_label}</small>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </section>

      <section className="gv-section" aria-labelledby="gv-gal-title">
        <h2 className="gv-h2" id="gv-gal-title">Galería</h2>
        <p className="gv-muted" style={{ marginTop: -6 }}>Fotos en preparación. Estos espacios se reemplazarán por fotos reales del proyecto.</p>
        <div className="gv-gallery">
          {GALLERY_SLOTS.map((name) => (
            <div key={name} className="gv-ph" role="img" aria-label={`Foto pendiente: ${name}`}>
              <span className="gv-ph-tag">Foto pendiente</span>
              <span>{name}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="gv-section" id="contacto" ref={formRef} aria-labelledby="gv-form-title" style={{ scrollMarginTop: 72 }}>
        <h2 className="gv-h2" id="gv-form-title">Quiero información</h2>
        <p className="gv-muted" style={{ marginTop: -6 }}>Déjanos tus datos y un asesor te contactará.</p>
        <form className="gv-form" onSubmit={submit} noValidate={false} data-lead-form>
          <label>Nombre completo *
            <input name="name" required minLength={2} maxLength={120} autoComplete="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label>Celular / WhatsApp *
            <input name="phone" required type="tel" inputMode="tel" minLength={7} maxLength={30} autoComplete="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </label>
          <label>Correo
            <input name="email" type="email" maxLength={160} autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </label>
          <label>Ciudad
            <input name="city" maxLength={80} autoComplete="address-level2" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          </label>
          <label>{unit} de interés
            <select name="lot" value={form.lot} onChange={(e) => setForm({ ...form, lot: e.target.value })}>
              <option value="">Sin preferencia</option>
              {lots.filter((l) => l.status !== 'sold').map((l) => (
                <option key={`${l.block || ''}-${l.number}`} value={l.number}>{unit} {l.number}{l.block ? ` · Manzana ${l.block}` : ''} — {l.status_label}</option>
              ))}
            </select>
          </label>
          <label>Mensaje
            <textarea name="message" rows={3} maxLength={1000} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
          </label>
          <div className="gv-hp" aria-hidden="true">
            <label>No llenar este campo
              <input name="website" tabIndex={-1} autoComplete="off" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
            </label>
          </div>
          <label className="gv-check">
            <input type="checkbox" name="consent" required checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} />
            <span>Acepto que me contacten por teléfono, WhatsApp o correo sobre este proyecto.</span>
          </label>
          {formMsg && <p className={`gv-msg ${formState === 'ok' ? 'gv-msg-ok' : 'gv-msg-err'}`} role="status">{formMsg}</p>}
          <button type="submit" className="gv-btn gv-btn-primary" disabled={formState === 'sending'}>
            {formState === 'sending' ? 'Enviando…' : 'Enviar'}
          </button>
        </form>
      </section>

      <p style={{ marginTop: 20 }}>
        <Link href="/ventas" className="gv-back">← Ver todos los proyectos</Link>
        {' · '}
        <a className="gv-back" href={INSTAGRAM_URL} target="_blank" rel="noopener noreferrer">Instagram @gacconstruye</a>
      </p>

      {selected && (
        <div className="gv-panel" role="dialog" aria-modal="false" aria-labelledby="gv-panel-title" data-lot-panel>
          <button type="button" className="gv-close" aria-label="Cerrar" onClick={() => setSelected(null)}>×</button>
          <h3 className="gv-h2" id="gv-panel-title" style={{ marginBottom: 4 }}>{unit} {selected.number}</h3>
          <span className={`gv-chip gv-s-${selected.status}`} style={{ border: 0 }}>{selected.status_label}</span>
          <dl>
            {selected.block && (<><dt>Manzana</dt><dd>{selected.block}</dd></>)}
            {selected.phase && (<><dt>Etapa</dt><dd>{selected.phase}</dd></>)}
            {formatM2(selected.area_m2) && (<><dt>Área</dt><dd>{formatM2(selected.area_m2)}</dd></>)}
            {selected.frontage_m != null && selected.depth_m != null && (<><dt>Medidas</dt><dd>{selected.frontage_m} × {selected.depth_m} m</dd></>)}
            {selected.orientation && (<><dt>Orientación</dt><dd>{selected.orientation}</dd></>)}
            <dt>Precio</dt><dd>{formatCOP(selected.price) || 'Consultar con un asesor'}</dd>
          </dl>
          {selected.status === 'sold' ? (
            <p className="gv-muted">Este {unit.toLowerCase()} ya fue vendido. Mira los disponibles en el mapa.</p>
          ) : (
            <div className="gv-row">
              <button type="button" className="gv-btn gv-btn-primary" onClick={() => interested(selected)}>Me interesa</button>
              {project?.whatsapp && (
                <a className="gv-btn gv-btn-wa" target="_blank" rel="noopener noreferrer"
                  href={whatsappHref(project.whatsapp, `Hola, me interesa el ${unit.toLowerCase()} ${selected.number} de ${project.name}.`)}>
                  WhatsApp
                </a>
              )}
            </div>
          )}
        </div>
      )}

      {project?.whatsapp && !selected && (
        <a className="gv-btn gv-btn-wa gv-wa-float" href={whatsappHref(project.whatsapp, waText)} target="_blank" rel="noopener noreferrer" aria-label="Escribir por WhatsApp">
          WhatsApp
        </a>
      )}
    </div>
  );
}
