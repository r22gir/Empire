import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { VENTAS_CSS, INSTAGRAM_URL } from './ventasShared';

export const metadata: Metadata = {
  title: 'Proyectos en venta — GAC',
  description: 'Proyectos de vivienda en venta. Disponibilidad de lotes en vivo.',
  robots: { index: false, follow: false, noarchive: true, nocache: true },
};

// The sales site belongs to Maxine (GAC). Other editions answer 404.
const SALES_EDITION = (process.env.NEXT_PUBLIC_EMPIRE_EDITION || '').trim().toLowerCase() === 'maxine';

export default function VentasLayout({ children }: { children: React.ReactNode }) {
  if (!SALES_EDITION) notFound();
  return (
    <div className="gv-root" data-ventas-page lang="es">
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700;900&display=swap"
      />
      <style dangerouslySetInnerHTML={{ __html: VENTAS_CSS }} />
      <header className="gv-header">
        <div className="gv-wrap gv-header-row">
          <Link href="/ventas" className="gv-brand" aria-label="Ir a todos los proyectos">
            <span className="gv-brand-mark">GAC</span>
            <span className="gv-brand-sub">Proyectos en venta</span>
          </Link>
          <a className="gv-ig" href={INSTAGRAM_URL} target="_blank" rel="noopener noreferrer">
            @gacconstruye
          </a>
        </div>
      </header>
      <main className="gv-main">{children}</main>
      <footer className="gv-footer">
        <div className="gv-wrap">
          <p>
            Síguenos en Instagram:{' '}
            <a href={INSTAGRAM_URL} target="_blank" rel="noopener noreferrer">@gacconstruye</a>
          </p>
          <p className="gv-muted">
            Información de referencia. Disponibilidad sujeta a confirmación con un asesor.
          </p>
        </div>
      </footer>
    </div>
  );
}
