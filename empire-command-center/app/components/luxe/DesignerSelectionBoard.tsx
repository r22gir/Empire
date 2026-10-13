'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { API } from '../../lib/api';
import {
  DEMO_BOARD,
  HOUSE_CATALOG,
  catalogIndex,
  composeEstimate,
  money,
  setSelectionQty,
  toggleSelection,
  type LuxeBoard,
  type LuxeKind,
} from '../../lib/luxe-board-logic';
import './designer-board.css';

function catalogField(item: object, key: string): string {
  const value = (item as Record<string, unknown>)[key];
  return typeof value === 'string' ? value : '';
}

export default function DesignerSelectionBoard() {
  const [catalog, setCatalog] = useState(HOUSE_CATALOG);
  const [tab, setTab] = useState<LuxeKind>('fabric');
  const [query, setQuery] = useState('');
  const [board, setBoard] = useState<LuxeBoard>(DEMO_BOARD);
  const [serverEstimate, setServerEstimate] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('Preview only. Nothing is written to live quotes or clients.');

  useEffect(() => {
    fetch(`${API}/luxe/catalog`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.fabrics) setCatalog({ fabrics: data.fabrics, finishes: data.finishes, photos: data.photos });
      })
      .catch(() => {/* catalog stays empty; demo board still paints via server later */});
    fetch(`${API}/luxe/boards/demo`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.board) setBoard({ ...DEMO_BOARD, ...data.board, id: 'demo' });
        if (data?.estimate) setServerEstimate(data.estimate);
      })
      .catch(() => undefined);
  }, []);

  const index = useMemo(() => catalogIndex(catalog), [catalog]);
  const local = useMemo(() => composeEstimate(board, index), [board, index]);
  const estimate = serverEstimate && serverEstimate.wrote_quote === false ? {
    ...local,
    materials: serverEstimate.materials ?? local.materials,
    labor: serverEstimate.labor ?? local.labor,
    subtotal: serverEstimate.subtotal ?? local.subtotal,
    deposit_suggested: serverEstimate.deposit_suggested ?? local.deposit_suggested,
    lines: serverEstimate.lines || local.lines,
  } : local;

  const pool = tab === 'fabric' ? catalog.fabrics : tab === 'finish' ? catalog.finishes : catalog.photos;
  const filtered = pool.filter((item) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    const extra = [
      'house' in item ? item.house : '',
      'color' in item ? item.color : '',
      'material' in item ? item.material : '',
      'room' in item ? item.room : '',
    ].filter(Boolean).join(' ');
    return `${item.name} ${extra}`.toLowerCase().includes(q);
  });

  async function preview() {
    setBusy(true);
    try {
      const res = await fetch(`${API}/luxe/estimate/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(board),
      });
      const data = await res.json();
      if (data?.estimate) setServerEstimate(data.estimate);
      setNote(data?.estimate?.disclaimer || 'Preview estimate composed. No live quote was written.');
    } catch {
      setNote('Working from the studio catalog locally. Still no live write.');
    }
    setBusy(false);
  }

  return (
    <div className="lxb" data-luxe-board="1">
      <header className="lxb-top">
        <div>
          <p className="lxb-kicker">LuxeForge · Atelier</p>
          <h1>Selection board</h1>
          <p>Compose fabrics, finishes, and rooms into a proposal. The estimate is a study — it never writes a live quote.</p>
        </div>
        <div className="lxb-meta">
          <label>Board title</label>
          <input value={board.title} onChange={(e) => setBoard({ ...board, title: e.target.value })} />
          <label>Client</label>
          <input value={board.client_name || ''} onChange={(e) => setBoard({ ...board, client_name: e.target.value })} />
          <label>Project</label>
          <input value={board.project_name || ''} onChange={(e) => setBoard({ ...board, project_name: e.target.value })} />
          <label>Treatment</label>
          <select value={board.treatment} onChange={(e) => setBoard({ ...board, treatment: e.target.value })}>
            <option value="drapery">Drapery</option>
            <option value="upholstery">Upholstery</option>
            <option value="roman">Roman shade</option>
            <option value="bedding">Bedding</option>
          </select>
        </div>
      </header>

      <div className="lxb-body">
        <aside className="lxb-rail">
          <div className="lxb-tabs" role="tablist">
            {([
              ['fabric', 'Fabrics'],
              ['finish', 'Finishes'],
              ['photo', 'Rooms'],
            ] as [LuxeKind, string][]).map(([id, label]) => (
              <button key={id} className={tab === id ? 'on' : ''} onClick={() => setTab(id)}>{label}</button>
            ))}
          </div>
          <input className="lxb-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search the house library" />
          {filtered.map((item) => {
            const on = board.selections.some((s) => s.id === item.id);
            return (
              <button key={item.id} className={`lxb-tile${on ? ' on' : ''}`} onClick={() => { setBoard(toggleSelection(board, item)); setServerEstimate(null); }}>
                <div className="lxb-swatch" style={{ background: item.swatch }} />
                <span>
                  <b>{item.name}</b>
                  <small>
                    {catalogField(item, 'house') || catalogField(item, 'family') || catalogField(item, 'room')} · {catalogField(item, 'color') || catalogField(item, 'mood') || catalogField(item, 'material')}
                    {item.kind === 'fabric' ? ` · ${money(item.price_per_yard || 0)} / yd` : item.kind === 'finish' ? ` · ${money(item.price || 0)}` : ''}
                  </small>
                </span>
              </button>
            );
          })}
          {filtered.length === 0 && <div className="lxb-disclaimer">Library loads from the studio catalog. The demo board still holds its pieces.</div>}
        </aside>

        <section className="lxb-stage">
          <h2>Composition</h2>
          {board.selections.length === 0 ? (
            <div className="lxb-empty">Pin a cloth, a finish, a room.</div>
          ) : (
            <div className="lxb-mosaic">
              {board.selections.map((sel) => {
                const item = index.get(sel.id);
                if (!item) return null;
                return (
                  <article key={sel.id} className="lxb-card">
                    <div className="lxb-swatch" style={{ background: item.swatch }} />
                    <b>{item.name}</b>
                    <small>{catalogField(item, 'house') || catalogField(item, 'family') || catalogField(item, 'room')}</small>
                    {item.kind !== 'photo' && (
                      <div>
                        <input
                          type="number"
                          min={1}
                          value={sel.qty || 1}
                          onChange={(e) => { setBoard(setSelectionQty(board, sel.id, Number(e.target.value || 1))); setServerEstimate(null); }}
                          aria-label={`${item.name} quantity`}
                        />
                        <small> {item.kind === 'fabric' ? 'yards' : item.unit || 'ea'}</small>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <aside className="lxb-sheet" data-luxe-estimate="1">
          <h2>Proposal</h2>
          <p className="lxb-disclaimer">{board.client_name || 'Client'} · {board.project_name || 'Untitled study'}</p>
          {(estimate.lines as any[]).map((line) => (
            <div className="lxb-line" key={line.id}>
              <div>
                {line.name}
                <em>{line.house || line.family} · {line.qty} {line.unit || (line.kind === 'fabric' ? 'yd' : '')}</em>
              </div>
              <div>{money(line.amount)}</div>
            </div>
          ))}
          {estimate.labor > 0 && !((estimate.lines as any[]).some((l) => l.kind === 'labor')) && (
            <div className="lxb-line">
              <div>Studio labor<em>{board.treatment}</em></div>
              <div>{money(estimate.labor)}</div>
            </div>
          )}
          <div className="lxb-totals">
            <div><span>Materials</span><span>{money(estimate.materials)}</span></div>
            <div><span>Labor</span><span>{money(estimate.labor)}</span></div>
            <div className="sum"><span>Study total</span><span>{money(estimate.subtotal)}</span></div>
            <div><span>Suggested deposit</span><span>{money(estimate.deposit_suggested)}</span></div>
          </div>
          <label className="lxb-disclaimer">Designer note</label>
          <textarea className="lxb-note" value={board.notes || ''} onChange={(e) => setBoard({ ...board, notes: e.target.value })} />
          <div className="lxb-actions">
            <button className="primary" disabled={busy} onClick={preview} data-compose-estimate="1">
              {busy ? 'Composing…' : 'Compose estimate'}
            </button>
          </div>
          <p className="lxb-disclaimer">{note}</p>
        </aside>
      </div>
    </div>
  );
}
