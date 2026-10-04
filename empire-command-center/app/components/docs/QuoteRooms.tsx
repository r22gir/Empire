'use client';
/**
 * Quote line items grouped by room (uses the existing line-item `room` field, e.g.
 * "LIVING ROOM — 1. Installation": room = part before " — ", sub-part after).
 * Items with no room form the "Job-wide" group (install, removal, delivery, travel...).
 * Move items by drag-and-drop or the "Move to" dropdown. Totals are computed by the caller
 * exactly as before; this only changes how rows are displayed and the item's room value.
 */
import { Fragment, useEffect, useMemo, useState, type ReactNode } from 'react';
import { ChevronDown, ChevronRight, GripVertical, Plus, ImageIcon, X } from 'lucide-react';
import './docs.css';

export const JOB_WIDE = 'Job-wide';
export const roomOf = (item: any): string => { const r = String(item?.room || '').trim(); const k = r.indexOf(' — '); return (k >= 0 ? r.slice(0, k) : r).trim(); };
export const subOf = (item: any): string => { const r = String(item?.room || ''); const k = r.indexOf(' — '); return k >= 0 ? r.slice(k + 3).trim() : ''; };

/** New items array with item `idx` moved into `target` room ('' = Job-wide), placed after that room's last row. */
export function moveToRoom(items: any[], idx: number, target: string): any[] {
  const out = [...items];
  const it = { ...out[idx] };
  const sub = subOf(it);
  it.room = target ? (sub ? `${target} — ${sub}` : target) : '';
  out.splice(idx, 1);
  let last = -1;
  out.forEach((x, i) => { if (roomOf(x) === target) last = i; });
  let pos = out.length;
  if (last >= 0) pos = last + 1;
  else if (target) { const j = out.findIndex(x => !roomOf(x)); if (j !== -1) pos = j; }
  out.splice(pos, 0, it);
  return out;
}

export interface RowCells { desc: ReactNode; qty: ReactNode; unit: ReactNode; rate: ReactNode; amount: ReactNode; remove: ReactNode }

interface Props {
  quoteId: string;
  items: any[];
  amountOf: (item: any) => number;
  renderCells: (item: any, idx: number) => RowCells;
  onMove: (idx: number, room: string) => void;
  onAddToRoom: (room: string) => void;
  photos?: { url: string; label: string }[];
}

const money = (n: number) => `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const th = (label: string, align: 'left' | 'right' | 'center', width?: number) =>
  <th style={{ textAlign: align, padding: '6px 8px', color: '#8fb3c2', fontSize: 11, fontWeight: 600, width }}>{label}</th>;

export default function QuoteRooms({ quoteId, items, amountOf, renderCells, onMove, onAddToRoom, photos = [] }: Props) {
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [dropRoom, setDropRoom] = useState<string | null>(null);
  const [roomPhotos, setRoomPhotos] = useState<Record<string, string>>({});
  const [picker, setPicker] = useState<string | null>(null);
  const storeKey = `empire.roomPhotos.${quoteId}`;
  useEffect(() => { try { setRoomPhotos(JSON.parse(localStorage.getItem(storeKey) || '{}')); } catch { setRoomPhotos({}); } }, [storeKey]);
  const setPhoto = (room: string, url: string | null) => {
    setRoomPhotos(prev => { const n = { ...prev }; if (url) n[room] = url; else delete n[room]; try { localStorage.setItem(storeKey, JSON.stringify(n)); } catch { /* ignore */ } return n; });
    setPicker(null);
  };

  const groups = useMemo(() => {
    const order: string[] = [];
    const map = new Map<string, number[]>();
    items.forEach((it, i) => { const r = roomOf(it); if (!map.has(r)) { map.set(r, []); if (r) order.push(r); } map.get(r)!.push(i); });
    const list = order.map(r => ({ key: r, label: r, idxs: map.get(r)! }));
    list.push({ key: '', label: JOB_WIDE, idxs: map.get('') || [] });
    return list;
  }, [items]);
  const roomNames = groups.filter(g => g.key).map(g => g.key);

  const toggle = (k: string) => setClosed(prev => { const n = new Set(prev); if (n.has(k)) n.delete(k); else n.add(k); return n; });
  const doMove = (idx: number, value: string) => {
    if (value === '__new') {
      const name = window.prompt('New room name (e.g. PRIMARY BEDROOM)');
      if (!name || !name.trim()) return;
      onMove(idx, name.trim().replace(/\s+—\s+/g, ' - '));
    } else onMove(idx, value === '__job' ? '' : value);
  };

  return (
    <div className="dh dh-rooms qr-rooms">
      {groups.map(g => {
        const open = !closed.has(g.key);
        const sub = g.idxs.reduce((t, i) => t + (amountOf(items[i]) || 0), 0);
        const photo = roomPhotos[g.label];
        let lastSub = '';
        return (
          <section key={g.key || '__job'} className={`dh-room${open ? ' is-open' : ''}${dropRoom === g.key ? ' is-drop' : ''}`}
            onDragOver={e => { if (dragIdx == null) return; e.preventDefault(); e.dataTransfer.dropEffect = 'move'; if (dropRoom !== g.key) setDropRoom(g.key); }}
            onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDropRoom(d => (d === g.key ? null : d)); }}
            onDrop={e => { e.preventDefault(); const i = Number(e.dataTransfer.getData('text/plain')); setDropRoom(null); setDragIdx(null); if (!isNaN(i) && roomOf(items[i]) !== g.key) onMove(i, g.key); }}>
            <header onClick={() => toggle(g.key)} role="button" tabIndex={0} aria-expanded={open}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(g.key); } }}>
              {open ? <ChevronDown size={15} style={{ color: '#00e5ff' }} /> : <ChevronRight size={15} style={{ color: '#00e5ff' }} />}
              {photos.length > 0 && (
                <button type="button" className="dh-room-photo" style={photo ? { backgroundImage: `url("${photo}")` } : undefined}
                  onClick={e => { e.stopPropagation(); setPicker(picker === g.label ? null : g.label); }} aria-label={`Room photo for ${g.label}`}
                  title={photo ? 'Change room photo' : 'Add a room photo'}>
                  {!photo && <ImageIcon size={16} style={{ color: '#5f8796', margin: 'auto' }} />}
                </button>
              )}
              <h3>{g.label}<small className="dh-num">{g.idxs.length} item{g.idxs.length === 1 ? '' : 's'}</small>{!g.key && <small>install, removal, delivery and other whole-job items</small>}</h3>
              <span className="dh-room-sub">{money(sub)}</span>
              <span className="dh-room-actions">
                <button type="button" className="dh-iconbtn" style={{ width: 30, height: 30 }} onClick={e => { e.stopPropagation(); onAddToRoom(g.key); }} aria-label={`Add a line to ${g.label}`} title={`Add a line to ${g.label}`}><Plus size={14} /></button>
              </span>
            </header>
            {picker === g.label && (
              <div style={{ padding: 8, display: 'flex', gap: 6, overflowX: 'auto', borderBottom: '1px solid var(--dh-line)' }}>
                {photos.map(p => (
                  <button key={p.url} type="button" onClick={() => setPhoto(g.label, p.url)} title={p.label}
                    style={{ width: 64, height: 64, flexShrink: 0, background: `#0b1d28 url("${p.url}") center/cover`, border: `1px solid ${photo === p.url ? '#00e5ff' : 'var(--dh-line)'}`, cursor: 'pointer' }} />
                ))}
                {photo && <button type="button" className="dh-act" onClick={() => setPhoto(g.label, null)}><X size={14} /> Remove</button>}
                <span className="dh-muted" style={{ fontSize: 11.5, alignSelf: 'center', whiteSpace: 'nowrap' }}>Saved on this device</span>
              </div>
            )}
            {open && (
              <div className="dh-room-body">
                {g.idxs.length === 0 ? (
                  <div className="dh-room-empty">{dragIdx != null ? 'Drop here to make it a job-wide item' : 'No job-wide items. Drag a row here or use "Move to".'}</div>
                ) : (
                  <table style={{ fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--dh-line)' }}>
                        <th style={{ width: 26 }} />{th('Description', 'left')}{th('Qty', 'right', 80)}{th('Unit', 'center', 64)}{th('Rate', 'right', 96)}{th('Amount', 'right', 100)}{th('Move to', 'left', 130)}<th style={{ width: 36 }} />
                      </tr>
                    </thead>
                    <tbody>
                      {g.idxs.map(i => {
                        const it = items[i];
                        const c = renderCells(it, i);
                        const s = subOf(it);
                        const head = s && s !== lastSub ? s : '';
                        lastSub = s || lastSub;
                        return (
                          <Fragment key={i}>
                            {head && <tr className="dh-subhead"><td colSpan={8}>{head}</td></tr>}
                            <tr className={`dh-item${dragIdx === i ? ' is-dragging' : ''}`} style={{ borderBottom: '1px solid rgba(120,200,220,0.08)' }}
                              draggable onDragStart={e => { e.dataTransfer.setData('text/plain', String(i)); e.dataTransfer.effectAllowed = 'move'; setDragIdx(i); }}
                              onDragEnd={() => { setDragIdx(null); setDropRoom(null); }}>
                              <td className="dh-c-drag" style={{ padding: '4px 0', verticalAlign: 'middle' }}><span className="dh-row-drag" title="Drag to another room" aria-hidden><GripVertical size={15} /></span></td>
                              <td className="dh-c-desc" style={{ padding: '4px 8px' }}>{c.desc}</td>
                              <td style={{ padding: '4px 4px' }}>{c.qty}</td>
                              <td style={{ padding: '4px 4px' }}>{c.unit}</td>
                              <td style={{ padding: '4px 4px' }}>{c.rate}</td>
                              <td className="dh-num" style={{ padding: '4px 8px', textAlign: 'right', fontWeight: 600, fontSize: 12.5, color: '#f2fbff', whiteSpace: 'nowrap' }}>{c.amount}</td>
                              <td className="dh-c-move" style={{ padding: '4px 4px' }}>
                                <select className="dh-input dh-move" value="" onChange={e => doMove(i, e.target.value)} aria-label="Move to room" style={{ minHeight: 30, width: '100%' }}>
                                  <option value="" disabled>Move to…</option>
                                  {roomNames.filter(r => r !== g.key).map(r => <option key={r} value={r}>{r}</option>)}
                                  {g.key !== '' && <option value="__job">{JOB_WIDE}</option>}
                                  <option value="__new">New room…</option>
                                </select>
                              </td>
                              <td style={{ padding: '4px 4px', textAlign: 'center' }}>{c.remove}</td>
                            </tr>
                          </Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
