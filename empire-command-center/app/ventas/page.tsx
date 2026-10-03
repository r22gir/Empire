'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PUBLIC_API, STATUS_LABEL, STATUS_ORDER, type PublicProject } from './ventasShared';

const BAR_COLORS: Record<string, string> = {
  available: '#208D63',
  reserved: '#ECA400',
  sold: '#8C9A94',
  consultar: '#CFE6DA',
};

export default function VentasHome() {
  const [projects, setProjects] = useState<PublicProject[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(`${PUBLIC_API}/projects`, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d) => alive && setProjects(d.projects || []))
      .catch(() => alive && setError(true));
    return () => { alive = false; };
  }, []);

  return (
    <div className="gv-wrap">
      <h1 className="gv-h1">Proyectos en venta</h1>
      <p className="gv-lead">
        Conoce nuestros proyectos, mira qué lotes y unidades están disponibles hoy y déjanos tus datos para que un asesor te contacte.
      </p>
      {error && <p className="gv-msg gv-msg-err">No pudimos cargar los proyectos. Intenta de nuevo en un momento.</p>}
      {!projects && !error && <p className="gv-muted">Cargando proyectos…</p>}
      {projects && projects.length === 0 && <p className="gv-muted">Pronto publicaremos nuestros proyectos.</p>}
      <div className="gv-grid">
        {(projects || []).map((p) => {
          const total = STATUS_ORDER.reduce((n, s) => n + (p.counts?.[s] || 0), 0);
          return (
            <Link key={p.slug} href={`/ventas/${p.slug}`} className="gv-card" data-project={p.slug}>
              <div className="gv-ph" role="img" aria-label={`Foto pendiente de ${p.name}`}>
                <span className="gv-ph-tag">Foto pendiente</span>
                <span>{p.name}<small>Espacio reservado para la foto del proyecto</small></span>
              </div>
              <div className="gv-card-body">
                <div className="gv-row">
                  <span className="gv-chip">{p.status}</span>
                  {p.counts?.available ? (
                    <span className="gv-chip gv-chip-acc">{p.counts.available} disponibles</span>
                  ) : null}
                </div>
                <h3>{p.name}</h3>
                {p.tagline && <p className="gv-lead" style={{ margin: 0, fontSize: 15 }}>{p.tagline}</p>}
                {p.location && <p className="gv-muted" style={{ margin: 0 }}>📍 {p.location}</p>}
                {total > 0 && (
                  <>
                    <div className="gv-bar" aria-hidden="true">
                      {STATUS_ORDER.map((s) => (p.counts?.[s] ? (
                        <span key={s} style={{ width: `${(p.counts[s] / total) * 100}%`, background: BAR_COLORS[s] }} />
                      ) : null))}
                    </div>
                    <div className="gv-counts">
                      {STATUS_ORDER.map((s) => (p.counts?.[s] ? (
                        <span key={s}><span className="gv-dot" style={{ background: BAR_COLORS[s] }} />{STATUS_LABEL[s]}: {p.counts[s]}</span>
                      ) : null))}
                    </div>
                  </>
                )}
                <span className="gv-btn gv-btn-primary" style={{ marginTop: 6 }}>Ver proyecto y lotes →</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
