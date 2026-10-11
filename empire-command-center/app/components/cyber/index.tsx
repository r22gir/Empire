'use client';
/**
 * Cyber theme components — thin wrappers over the cy-* classes in
 * app/theme/cyber.css. Presentational only: no data fetching, no state
 * beyond the modal's Escape handler.
 */
import '../../theme/cyber.css';
import { useEffect, useId, type ReactNode, type ButtonHTMLAttributes, type InputHTMLAttributes,
  type SelectHTMLAttributes, type TextareaHTMLAttributes, type AnchorHTMLAttributes, type HTMLAttributes } from 'react';

const cx = (...c: Array<string | false | null | undefined>) => c.filter(Boolean).join(' ');

type Tone = 'default' | 'alert';

export function CyberPanel({ title, icon, source, actions, tone = 'default', hud = true, className, children, ...rest }:
  { title?: ReactNode; icon?: ReactNode; source?: ReactNode; actions?: ReactNode; tone?: Tone; hud?: boolean } & HTMLAttributes<HTMLElement>) {
  return (
    <section className={cx('cy-panel', hud && 'cy-hud', tone === 'alert' && 'is-alert', className)} {...rest}>
      {(title || actions) && (
        <header className="cy-panel-head">
          {title && <h2 className="cy-panel-title">{icon}{title}</h2>}
          {actions}
        </header>
      )}
      {children}
      {source && <div className="cy-src" style={{ marginTop: 8 }}>{source}</div>}
    </section>
  );
}

export function CyberCard({ active, tone = 'default', hud, href, className, children, ...rest }:
  { active?: boolean; tone?: Tone; hud?: boolean; href?: string } & HTMLAttributes<HTMLElement>) {
  const cls = cx('cy-card', hud && 'cy-hud', active && 'is-active', tone === 'alert' && 'is-alert', className);
  if (href) return <a href={href} className={cls} {...(rest as AnchorHTMLAttributes<HTMLAnchorElement>)}>{children}</a>;
  return <div className={cls} {...rest}>{children}</div>;
}

export function CyberKpi({ label, value, sub, tone = 'default' }: { label: ReactNode; value: ReactNode; sub?: ReactNode; tone?: Tone }) {
  return (
    <div className={tone === 'alert' ? 'is-alert' : undefined}>
      <div className="cy-kpi-label">{label}</div>
      <div className="cy-kpi">{value ?? '—'}</div>
      {sub && <div className="cy-src" style={{ marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

type BtnVariant = 'default' | 'primary' | 'danger' | 'ghost';
export function CyberButton({ variant = 'default', size, className, children, ...rest }:
  { variant?: BtnVariant; size?: 'sm' } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" className={cx('cy-btn', variant !== 'default' && `is-${variant}`, size === 'sm' && 'is-sm', className)} {...rest}>
      {children}
    </button>
  );
}

export function CyberLinkButton({ variant = 'default', size, className, children, ...rest }:
  { variant?: BtnVariant; size?: 'sm' } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return <a className={cx('cy-btn', variant !== 'default' && `is-${variant}`, size === 'sm' && 'is-sm', className)} {...rest}>{children}</a>;
}

export function CyberTab({ icon, label, badge, active, tone = 'default', href, className, ...rest }:
  { icon?: ReactNode; label: ReactNode; badge?: ReactNode; active?: boolean; tone?: Tone; href?: string } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const cls = cx('cy-tab', active && 'is-active', tone === 'alert' && 'is-alert', className);
  const inner = (<>
    {icon && <span className="cy-tab-ico">{icon}</span>}
    <span className="cy-tab-label">{label}</span>
    {badge != null && <span className="cy-tab-badge">{badge}</span>}
  </>);
  if (href) return <a href={href} className={cls} aria-current={active ? 'page' : undefined}>{inner}</a>;
  return <button type="button" className={cls} aria-current={active ? 'page' : undefined} {...rest}>{inner}</button>;
}

function Field({ label, hint, error, id, children }: { label?: ReactNode; hint?: ReactNode; error?: ReactNode; id: string; children: ReactNode }) {
  return (
    <div className="cy-field">
      {label && <label className="cy-label" htmlFor={id}>{label}</label>}
      {children}
      {(error || hint) && <div className={cx('cy-hint', !!error && 'is-error')}>{error || hint}</div>}
    </div>
  );
}

export function CyberInput({ label, hint, error, id, className, ...rest }:
  { label?: ReactNode; hint?: ReactNode; error?: ReactNode } & InputHTMLAttributes<HTMLInputElement>) {
  const auto = useId(); const fid = id || auto;
  return <Field label={label} hint={hint} error={error} id={fid}><input id={fid} className={cx('cy-input', className)} aria-invalid={!!error || undefined} {...rest} /></Field>;
}

export function CyberSelect({ label, hint, error, id, className, children, ...rest }:
  { label?: ReactNode; hint?: ReactNode; error?: ReactNode } & SelectHTMLAttributes<HTMLSelectElement>) {
  const auto = useId(); const fid = id || auto;
  return <Field label={label} hint={hint} error={error} id={fid}><select id={fid} className={cx('cy-input', className)} {...rest}>{children}</select></Field>;
}

export function CyberTextarea({ label, hint, error, id, className, ...rest }:
  { label?: ReactNode; hint?: ReactNode; error?: ReactNode } & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const auto = useId(); const fid = id || auto;
  return <Field label={label} hint={hint} error={error} id={fid}><textarea id={fid} className={cx('cy-input', className)} {...rest} /></Field>;
}

export type CyberColumn<T> = { key: string; header: ReactNode; render?: (row: T) => ReactNode; numeric?: boolean };
export function CyberTable<T extends Record<string, any>>({ columns, rows, rowKey, empty = 'SIN DATOS · NO DATA', onRowClick }:
  { columns: CyberColumn<T>[]; rows: T[] | null | undefined; rowKey: (row: T, i: number) => string; empty?: ReactNode; onRowClick?: (row: T) => void }) {
  if (!rows || rows.length === 0) return <div className="cy-nodata">{empty}</div>;
  return (
    <div className="cy-table-wrap">
      <table className="cy-table">
        <thead><tr>{columns.map(c => <th key={c.key} className={c.numeric ? 'is-num' : undefined}>{c.header}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={rowKey(r, i)} onClick={onRowClick ? () => onRowClick(r) : undefined} style={onRowClick ? { cursor: 'pointer' } : undefined}>
              {columns.map(c => <td key={c.key} className={c.numeric ? 'is-num' : undefined}>{c.render ? c.render(r) : String(r[c.key] ?? '—')}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function CyberPill({ tone, children }: { tone?: 'ok' | 'warn' | 'alert' | 'muted'; children: ReactNode }) {
  return <span className={cx('cy-pill', tone && `is-${tone}`)}>{children}</span>;
}

export function CyberNoData({ reason }: { reason?: ReactNode }) {
  return <div className="cy-nodata">SIN DATOS · NO DATA{reason && <span>{reason}</span>}</div>;
}

export function CyberBackLink({ href = '/', children = 'Back' }: { href?: string; children?: ReactNode }) {
  return <a className="cy-back" href={href}>← {children}</a>;
}

export function CyberModal({ open, title, onClose, footer, children }:
  { open: boolean; title?: ReactNode; onClose: () => void; footer?: ReactNode; children: ReactNode }) {
  const tid = useId();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="cy-modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="cy-modal cy-hud" role="dialog" aria-modal="true" aria-labelledby={title ? tid : undefined}>
        <div className="cy-modal-head">
          {title && <h2 id={tid} className="cy-panel-title">{title}</h2>}
          <button type="button" className="cy-btn is-ghost is-sm" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="cy-modal-body">{children}</div>
        {footer && <div className="cy-modal-foot">{footer}</div>}
      </div>
    </div>
  );
}
