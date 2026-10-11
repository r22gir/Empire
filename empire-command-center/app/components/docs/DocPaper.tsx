'use client';
/**
 * WYSIWYG document page body shared by quotes and invoices: line items grouped by room
 * (room = text before " — " in the line's `room`, sub-part after it, exactly how the estimate
 * PDF prints its sections), click a line to edit it in place, drag or "Move to" between rooms,
 * add lines per room, live subtotals. The caller owns the items array and the totals.
 */
import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { GripVertical, Trash2, Check, Plus, ChevronDown, ChevronRight, ImageIcon, X } from 'lucide-react';
import { JOB_WIDE, roomOf, subOf } from './QuoteRooms';
import './paper.css';

const UNITS = ['ea', 'sqft', 'sf', 'yd', 'hr', 'lf', 'panels', 'widths', 'set'];
export const money2 = (n: number) => `$${(Number(n) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** Stable order: rooms in first-appearance order, sub-parts grouped inside each room, job-wide last.
 *  Saving in this order makes the client PDF print the same sections as the page. */
export function orderByRoom<T>(items: T[]): T[] {
  const roomOrder: string[] = []; const subOrder = new Map<string, string[]>();
  items.forEach(it => {
    const r = roomOf(it); const s = subOf(it);
    if (!roomOrder.includes(r)) roomOrder.push(r);
    const so = subOrder.get(r) || []; if (!so.includes(s)) so.push(s); subOrder.set(r, so);
  });
  const rank = (it: T) => { const r = roomOf(it); const ri = r ? roomOrder.indexOf(r) : 1e6; return ri * 1000 + (subOrder.get(r) || []).indexOf(subOf(it)); };
  return items.map((it, i) => ({ it, i, k: rank(it) })).sort((a, b) => a.k - b.k || a.i - b.i).map(x => x.it);
}

export interface PaperLineFields { qty: string; rate: string; unit: string; desc: string }
interface Props {
  items: any[];
  fields?: PaperLineFields;                       // which keys hold qty / rate / unit / description
  amountOf: (item: any) => number;
  editable: boolean;
  onRequestEdit?: () => void;                     // click on a line while read-only
  onChange: (idx: number, field: string, value: any) => void;
  onRemove: (idx: number) => void;
  onMove: (idx: number, room: string) => void;
  onAdd: (room: string) => void;
  photos?: { url: string; label: string }[];
  photoKey?: string;                              // localStorage key for room photos
  showJobWide?: boolean;
}

export default function DocPaper({ items, fields = { qty: 'quantity', rate: 'rate', unit: 'unit', desc: 'description' }, amountOf, editable, onRequestEdit, onChange, onRemove, onMove, onAdd, photos = [], photoKey, showJobWide = true }: Props) {
  const [editing, setEditing] = useState<number | null>(null);
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [dropRoom, setDropRoom] = useState<string | null>(null);
  const [roomPhotos, setRoomPhotos] = useState<Record<string, string>>({});
  const [picker, setPicker] = useState<string | null>(null);
  const editRow = useRef<HTMLTableRowElement | null>(null);
  const [pendingAdd, setPendingAdd] = useState<string | null>(null);
  useEffect(() => { // open the line that was just added
    if (pendingAdd == null) return;
    for (let i = items.length - 1; i >= 0; i--) if (roomOf(items[i]) === pendingAdd && !items[i][fields.desc]) { setEditing(i); break; }
    setPendingAdd(null);
  }, [items]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (!photoKey) return; try { setRoomPhotos(JSON.parse(localStorage.getItem(photoKey) || '{}')); } catch { setRoomPhotos({}); } }, [photoKey]);
  const setPhoto = (room: string, url: string | null) => {
    setRoomPhotos(prev => { const n = { ...prev }; if (url) n[room] = url; else delete n[room]; try { if (photoKey) localStorage.setItem(photoKey, JSON.stringify(n)); } catch { /* ignore */ } return n; });
    setPicker(null);
  };
  useEffect(() => { if (!editable) setEditing(null); }, [editable]);
  useEffect(() => {
    if (editing == null) return;
    const away = (e: MouseEvent) => { const t = e.target as Node; if (editRow.current && !editRow.current.contains(t) && !(t as HTMLElement).closest?.('.qp-line')) setEditing(null); };
    document.addEventListener('mousedown', away);
    return () => document.removeEventListener('mousedown', away);
  }, [editing]);
  useEffect(() => { if (editing != null && editing >= items.length) setEditing(null); }, [items.length, editing]);

  const rooms = useMemo(() => {
    const order: string[] = []; const map = new Map<string, number[]>();
    items.forEach((it, i) => { const r = roomOf(it); if (!map.has(r)) { map.set(r, []); if (r) order.push(r); } map.get(r)!.push(i); });
    const list = order.map(r => ({ key: r, label: r, idxs: map.get(r)! }));
    if (showJobWide && ((map.get('') || []).length || editable)) list.push({ key: '', label: order.length ? JOB_WIDE : 'Items', idxs: map.get('') || [] });
    return list;
  }, [items, showJobWide, editable]);
  const roomNames = rooms.filter(r => r.key).map(r => r.key);

  const startEdit = (i: number) => { if (!editable) { onRequestEdit?.(); if (!onRequestEdit) return; } setEditing(i); };
  const moveTo = (i: number, v: string) => {
    if (v === '__new') { const n = window.prompt('New room name (e.g. PRIMARY BEDROOM)'); if (n && n.trim()) onMove(i, n.trim().replace(/\s+—\s+/g, ' - ')); }
    else onMove(i, v === '__job' ? '' : v);
    setEditing(null);
  };

  return (
    <div className="qp-rooms">
      <datalist id="qp-units">{UNITS.map(u => <option key={u} value={u} />)}</datalist>
      {rooms.map(g => {
        const open = !closed.has(g.key);
        const total = g.idxs.reduce((t, i) => t + (amountOf(items[i]) || 0), 0);
        // sub-parts in order of appearance inside the room
        const subs: { s: string; idxs: number[] }[] = [];
        g.idxs.forEach(i => { const s = subOf(items[i]); const f = subs.find(x => x.s === s); if (f) f.idxs.push(i); else subs.push({ s, idxs: [i] }); });
        const photo = roomPhotos[g.label];
        return (
          <section key={g.key || '__job'} className={`qp-room${dropRoom === g.key ? ' is-drop' : ''}`}
            onDragOver={e => { if (dragIdx == null) return; e.preventDefault(); if (dropRoom !== g.key) setDropRoom(g.key); }}
            onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDropRoom(d => (d === g.key ? null : d)); }}
            onDrop={e => { e.preventDefault(); const i = Number(e.dataTransfer.getData('text/plain')); setDropRoom(null); setDragIdx(null); if (!isNaN(i) && roomOf(items[i]) !== g.key) onMove(i, g.key); }}>
            <div className="qp-roomhead">
              <button type="button" onClick={() => setClosed(p => { const n = new Set(p); if (n.has(g.key)) n.delete(g.key); else n.add(g.key); return n; })} aria-expanded={open} aria-label={`${open ? 'Collapse' : 'Expand'} ${g.label}`}>
                {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
              </button>
              {(photo || (editable && photos.length > 0)) && (
                <button type="button" className="qp-roomphoto" style={photo ? { backgroundImage: `url("${photo}")` } : undefined} onClick={() => editable && setPicker(picker === g.label ? null : g.label)} aria-label={`Room photo for ${g.label}`}>
                  {!photo && <ImageIcon size={15} style={{ margin: 'auto' }} />}
                </button>
              )}
              <h3>{g.label}<small>{g.idxs.length} line{g.idxs.length === 1 ? '' : 's'}{!g.key && rooms.length > 1 ? ' · install, removal, delivery and other whole-job items' : ''}</small></h3>
              <span className="qp-roomtotal">{money2(total)}</span>
            </div>
            {picker === g.label && (
              <div style={{ display: 'flex', gap: 6, padding: '6px 0', overflowX: 'auto', alignItems: 'center' }}>
                {photos.map(p => <button key={p.url} type="button" onClick={() => setPhoto(g.label, p.url)} title={p.label} style={{ width: 56, height: 56, flexShrink: 0, background: `#ddd url("${p.url}") center/cover`, border: `2px solid ${photo === p.url ? '#b8902e' : 'transparent'}`, cursor: 'pointer' }} />)}
                {photo && <button type="button" className="qp-addline" onClick={() => setPhoto(g.label, null)}><X size={13} /> Remove photo</button>}
                <small style={{ color: '#6b6457', whiteSpace: 'nowrap' }}>Shown on this page only (saved on this device)</small>
              </div>
            )}
            {open && (
              <>
                {g.idxs.length === 0 && <div className="qp-empty">{dragIdx != null ? 'Drop here to make it a job-wide line.' : 'No job-wide lines. Add install, removal or delivery here, or drag a line in.'}</div>}
                {subs.map(sp => {
                  const st = sp.idxs.reduce((t, i) => t + (amountOf(items[i]) || 0), 0);
                  return (
                    <div key={sp.s || '_'} className="qp-sub">
                      {sp.s && <div className="qp-sublabel">{g.label} — {sp.s}</div>}
                      <table>
                        <colgroup><col style={{ width: 22 }} /><col /><col style={{ width: '11%' }} /><col style={{ width: '12%' }} /><col style={{ width: '13%' }} /><col style={{ width: 66 }} /></colgroup>
                        <thead><tr><th aria-label="Drag" /><th>Description</th><th className="r">Qty</th><th className="r">Rate</th><th className="r">Amount</th><th aria-label="Tools" /></tr></thead>
                        <tbody>
                          {sp.idxs.map(i => {
                            const it = items[i]; const isEd = editing === i && editable;
                            return (
                              <tr key={i} ref={isEd ? editRow : undefined} className={`qp-line${isEd ? ' is-editing' : ''}${dragIdx === i ? ' is-drag' : ''}`}
                                draggable={editable && !isEd} onDragStart={e => { e.dataTransfer.setData('text/plain', String(i)); e.dataTransfer.effectAllowed = 'move'; setDragIdx(i); }} onDragEnd={() => { setDragIdx(null); setDropRoom(null); }}
                                onClick={() => { if (!isEd) startEdit(i); }}
                                onKeyDown={e => { if (e.key === 'Escape') setEditing(null); if (e.key === 'Enter' && !isEd && (e.target as HTMLElement).tagName === 'TR') startEdit(i); }}
                                tabIndex={isEd ? -1 : 0} aria-label={`${it[fields.desc] || 'Line'} ${money2(amountOf(it))}${editable ? ', click to edit' : ''}`}>
                                <td className="c-grip">{editable && <span className="qp-grip" title="Drag to another room" aria-hidden><GripVertical size={13} /></span>}</td>
                                <td className="c-desc">
                                  {isEd ? (<>
                                    <textarea autoFocus rows={2} value={it[fields.desc] || ''} onChange={e => onChange(i, fields.desc, e.target.value)} aria-label="Description" onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) setEditing(null); }} />
                                    <select className="qp-move" value="" onChange={e => moveTo(i, e.target.value)} aria-label="Move to room">
                                      <option value="" disabled>Move to room…</option>
                                      {roomNames.filter(r => r !== g.key).map(r => <option key={r} value={r}>{r}</option>)}
                                      {g.key !== '' && <option value="__job">{JOB_WIDE}</option>}
                                      <option value="__new">New room…</option>
                                    </select>
                                  </>) : (<>
                                    {it[fields.desc] || <i style={{ color: '#9a917f' }}>New line: click to describe</i>}
                                    {it.price_overridden ? <span style={{ marginLeft: 6, fontSize: 9.5, fontWeight: 700, color: '#7c5a00', background: '#fcf3cf', border: '1px solid #e0b700', padding: '0 4px' }}>FOUNDER PRICE</span> : null}
                                  </>)}
                                </td>
                                <td className="r num c-qty">
                                  {isEd ? (<div style={{ display: 'flex', gap: 3 }}>
                                    <input className="r" type="number" step="0.01" value={it[fields.qty] ?? ''} onChange={e => onChange(i, fields.qty, parseFloat(e.target.value) || 0)} aria-label="Quantity" />
                                    <input list="qp-units" value={it[fields.unit] || ''} onChange={e => onChange(i, fields.unit, e.target.value)} aria-label="Unit" style={{ width: 54 }} />
                                  </div>) : <>{Number(it[fields.qty] ?? 0).toLocaleString('en-US', { maximumFractionDigits: 2 })} {it[fields.unit] || ''}</>}
                                </td>
                                <td className="r num c-rate">
                                  {isEd ? <input className="r" type="number" step="0.01" value={it[fields.rate] ?? ''} onChange={e => onChange(i, fields.rate, parseFloat(e.target.value) || 0)} aria-label="Rate" />
                                    : money2(Number(it[fields.rate] ?? 0))}
                                </td>
                                <td className="r num c-amt">{money2(amountOf(it))}</td>
                                <td className="c-tools">
                                  {editable && <div className="qp-tools">
                                    {isEd && <button type="button" onClick={e => { e.stopPropagation(); setEditing(null); }} aria-label="Done editing line" title="Done"><Check size={14} /></button>}
                                    <button type="button" onClick={e => { e.stopPropagation(); if (window.confirm('Remove this line?')) { onRemove(i); setEditing(null); } }} aria-label="Remove line" title="Remove line"><Trash2 size={13} /></button>
                                  </div>}
                                </td>
                              </tr>
                            );
                          })}
                          {(subs.length > 1 || sp.s) && <tr className="qp-subtotal"><td colSpan={4}>SUBTOTAL — {g.label}{sp.s ? ` — ${sp.s}` : ''}</td><td className="r num">{money2(st)}</td><td /></tr>}
                        </tbody>
                      </table>
                    </div>
                  );
                })}
                {editable && <button type="button" className="qp-addline" onClick={() => { setPendingAdd(g.key); onAdd(g.key); }}><Plus size={13} /> Add a line to {g.label}</button>}
              </>
            )}
          </section>
        );
      })}
    </div>
  );
}
