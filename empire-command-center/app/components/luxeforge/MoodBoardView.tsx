'use client';

import { useCallback, useEffect, useState } from 'react';
import { Copy, Image as ImageIcon, Palette, Plus, Share2, StickyNote, Trash2 } from 'lucide-react';
import { API } from '../../lib/api';
import { inchesToFraction } from '../../lib/fractions';

const MB = `${API}/luxeforge/mood-boards`;
const FABRIC_RE = /^V\d{3}-[A-Za-z][A-Za-z0-9]+$/;

type BoardSummary = {
  id: string;
  title: string;
  designer?: string;
  client_name?: string;
  share_token?: string;
  image_count?: number;
  swatch_count?: number;
};

type Board = BoardSummary & {
  description?: string;
  images?: Array<{ id: string; url: string; caption?: string; width_fraction?: string; height_fraction?: string; size_fraction?: string }>;
  swatches?: Array<{ id: string; fabric_code: string; name?: string; hex?: string; notes?: string; size_fraction?: string }>;
  notes?: Array<{ id: string; text: string; created_at?: string }>;
};

export default function MoodBoardView({ readOnly = false, sharedBoard = null }: { readOnly?: boolean; sharedBoard?: Board | null }) {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [active, setActive] = useState<Board | null>(sharedBoard);
  const [title, setTitle] = useState('New mood board');
  const [imageUrl, setImageUrl] = useState('');
  const [imageCaption, setImageCaption] = useState('');
  const [imageW, setImageW] = useState('');
  const [imageH, setImageH] = useState('');
  const [swatchCode, setSwatchCode] = useState('V142-Navy');
  const [swatchName, setSwatchName] = useState('');
  const [swatchHex, setSwatchHex] = useState('#1d3557');
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadList = useCallback(async () => {
    if (readOnly) return;
    const res = await fetch(MB);
    if (!res.ok) throw new Error('Mood boards unavailable');
    const data = await res.json();
    setBoards(data.items || []);
  }, [readOnly]);

  const openBoard = async (id: string) => {
    const res = await fetch(`${MB}/${id}`);
    if (!res.ok) return;
    setActive(await res.json());
  };

  useEffect(() => {
    if (sharedBoard) setActive(sharedBoard);
    else loadList().catch(err => setError(err.message));
  }, [sharedBoard, loadList]);

  const createBoard = async () => {
    setError(null);
    const res = await fetch(MB, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) { setError('Could not create board'); return; }
    const board = await res.json();
    setActive(board);
    await loadList();
  };

  const addImage = async () => {
    if (!active) return;
    const res = await fetch(`${MB}/${active.id}/images`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: imageUrl,
        caption: imageCaption,
        width_in: imageW ? Number(imageW) : null,
        height_in: imageH ? Number(imageH) : null,
      }),
    });
    if (!res.ok) { setError('Image URL required'); return; }
    setActive(await res.json());
    setImageUrl('');
    setImageCaption('');
  };

  const addSwatch = async () => {
    if (!active) return;
    if (!FABRIC_RE.test(swatchCode)) {
      setError('Fabric code must look like V142-Navy');
      return;
    }
    const res = await fetch(`${MB}/${active.id}/swatches`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fabric_code: swatchCode, name: swatchName, hex_color: swatchHex }),
    });
    if (!res.ok) { setError('Swatch rejected — use V###-Color'); return; }
    setActive(await res.json());
  };

  const addNote = async () => {
    if (!active || !note.trim()) return;
    const res = await fetch(`${MB}/${active.id}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: note }),
    });
    setActive(await res.json());
    setNote('');
  };

  const removeItem = async (collection: string, id: string) => {
    if (!active || readOnly) return;
    const res = await fetch(`${MB}/${active.id}/${collection}/${id}`, { method: 'DELETE' });
    if (res.ok) setActive(await res.json());
  };

  const shareUrl = active?.share_token
    ? `${typeof window !== 'undefined' ? window.location.origin : ''}/mood-board/${active.share_token}`
    : '';

  const copyShare = async () => {
    if (!shareUrl) return;
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: '#1a1a1a' }}>
            {readOnly ? active?.title || 'Mood board' : 'Designer mood boards'}
          </h2>
          <p style={{ fontSize: 12, color: '#888', margin: '4px 0 0' }}>
            Inspiration only — images, V###-Color swatches, and notes. Separate from the fabric selection board.
          </p>
        </div>
        {active?.share_token && (
          <button onClick={copyShare} style={{ display: 'flex', alignItems: 'center', gap: 6, border: '1px solid #ddd6fe', background: '#f5f3ff', color: '#6d28d9', borderRadius: 10, padding: '8px 12px', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
            {copied ? <Copy size={14} /> : <Share2 size={14} />}
            {copied ? 'Copied' : 'Share read-only'}
          </button>
        )}
      </div>

      {error && <div style={{ background: '#fef2f2', color: '#b91c1c', padding: 10, borderRadius: 10, fontSize: 12, marginBottom: 12 }}>{error}</div>}

      {!readOnly && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {boards.map(b => (
            <button key={b.id} onClick={() => openBoard(b.id)} style={{
              padding: '8px 12px', borderRadius: 10, border: active?.id === b.id ? '1.5px solid #7c3aed' : '1px solid #ece8e0',
              background: active?.id === b.id ? '#f5f3ff' : '#fff', color: '#333', fontSize: 12, cursor: 'pointer',
            }}>
              {b.title} · {b.swatch_count || 0} swatches
            </button>
          ))}
          <input value={title} onChange={e => setTitle(e.target.value)} style={{ padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 10, fontSize: 12 }} />
          <button onClick={createBoard} style={{ display: 'flex', alignItems: 'center', gap: 4, background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 10, padding: '8px 12px', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
            <Plus size={14} /> New board
          </button>
        </div>
      )}

      {!active && <div style={{ padding: 32, textAlign: 'center', color: '#aaa', fontSize: 13 }}>Create a board to pin images and fabric swatches.</div>}

      {active && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(280px, 1fr)', gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              <ImageIcon size={14} /> Images
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10, marginBottom: 14 }}>
              {(active.images || []).map(img => (
                <div key={img.id} style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 14, overflow: 'hidden' }}>
                  <div style={{ aspectRatio: '4 / 3', background: '#f5f2ed' }}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={img.url} alt={img.caption || ''} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  </div>
                  <div style={{ padding: 10 }}>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{img.caption || 'Untitled'}</div>
                    {img.size_fraction && <div style={{ fontSize: 11, color: '#7c3aed' }}>{img.size_fraction}</div>}
                    {!readOnly && <button onClick={() => removeItem('images', img.id)} style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer', padding: 0, marginTop: 4 }}><Trash2 size={12} /></button>}
                  </div>
                </div>
              ))}
            </div>
            {!readOnly && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <input value={imageUrl} onChange={e => setImageUrl(e.target.value)} placeholder="Image URL" style={{ flex: 1, minWidth: 180, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
                <input value={imageCaption} onChange={e => setImageCaption(e.target.value)} placeholder="Caption" style={{ width: 120, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
                <input value={imageW} onChange={e => setImageW(e.target.value)} placeholder='W in' style={{ width: 70, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
                <input value={imageH} onChange={e => setImageH(e.target.value)} placeholder='H in' style={{ width: 70, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
                <button onClick={addImage} style={{ background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 10px', fontSize: 12, cursor: 'pointer' }}>Add</button>
              </div>
            )}
            {(imageW || imageH) && (
              <div style={{ fontSize: 11, color: '#888', marginTop: 6 }}>Preview: {inchesToFraction(imageW)} × {inchesToFraction(imageH)}</div>
            )}
          </div>

          <div>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Palette size={14} /> Swatches
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
              {(active.swatches || []).map(s => (
                <div key={s.id} style={{ display: 'flex', gap: 10, alignItems: 'center', background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: 10 }}>
                  <div style={{ width: 36, height: 36, borderRadius: 8, background: s.hex || '#c9a84c', border: '1px solid #eee' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 700 }}>{s.fabric_code}</div>
                    <div style={{ fontSize: 11, color: '#888' }}>{s.name || 'Swatch'}{s.size_fraction ? ` · ${s.size_fraction}` : ''}</div>
                  </div>
                  {!readOnly && <button onClick={() => removeItem('swatches', s.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#aaa' }}><Trash2 size={12} /></button>}
                </div>
              ))}
            </div>
            {!readOnly && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
                <input value={swatchCode} onChange={e => setSwatchCode(e.target.value)} placeholder="V142-Navy" style={{ width: 110, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
                <input value={swatchName} onChange={e => setSwatchName(e.target.value)} placeholder="Name" style={{ width: 90, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
                <input value={swatchHex} onChange={e => setSwatchHex(e.target.value)} style={{ width: 80, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
                <button onClick={addSwatch} style={{ background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 10px', fontSize: 12, cursor: 'pointer' }}>Add</button>
              </div>
            )}

            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              <StickyNote size={14} /> Notes
            </div>
            {(active.notes || []).map(n => (
              <div key={n.id} style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10, padding: 10, fontSize: 12, marginBottom: 8 }}>
                {n.text}
              </div>
            ))}
            {!readOnly && (
              <div style={{ display: 'flex', gap: 6 }}>
                <input value={note} onChange={e => setNote(e.target.value)} placeholder="Designer note" style={{ flex: 1, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
                <button onClick={addNote} style={{ background: '#111', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 10px', fontSize: 12, cursor: 'pointer' }}>Add</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
