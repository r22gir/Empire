'use client';
import { useState, useCallback, useRef } from 'react';

const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : 'http://localhost:8000/api/v1';

const ITEM_TYPES: { id: string; label: string; icon: string }[] = [
  { id: 'bench', label: 'Bench / Banquette', icon: '🪑' },
  { id: 'window', label: 'Window Treatment', icon: '🪟' },
  { id: 'pillow', label: 'Pillow / Cushion', icon: '🛋' },
  { id: 'upholstery', label: 'Upholstery', icon: '💺' },
  { id: 'table', label: 'Table / Console', icon: '🪵' },
  { id: 'generic', label: 'Other', icon: '📐' },
];

export default function DrawingStudioPage() {
  const [itemType, setItemType] = useState('generic');
  const [name, setName] = useState('');
  const [quoteNum, setQuoteNum] = useState('');
  const [notes, setNotes] = useState('');
  const [dimensions, setDimensions] = useState<Record<string, string>>({});
  const [newDimLabel, setNewDimLabel] = useState('');
  const [newDimValue, setNewDimValue] = useState('');
  const [svgPreview, setSvgPreview] = useState('');
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [sketchLoading, setSketchLoading] = useState(false);
  const [sketchPreview, setSketchPreview] = useState('');

  // Bench-specific
  const [benchType, setBenchType] = useState('straight');
  const [lf, setLf] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const showStatus = (msg: string, duration = 4000) => {
    setStatusMsg(msg);
    if (duration > 0) setTimeout(() => setStatusMsg(''), duration);
  };

  const addDimension = () => {
    if (!newDimLabel.trim() || !newDimValue.trim()) return;
    setDimensions(prev => ({ ...prev, [newDimLabel.trim()]: newDimValue.trim() }));
    setNewDimLabel('');
    setNewDimValue('');
  };

  const removeDimension = (key: string) => {
    setDimensions(prev => {
      const copy = { ...prev };
      delete copy[key];
      return copy;
    });
  };

  const handleSketchUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSketchLoading(true);
    setStatusMsg('');
    try {
      const reader = new FileReader();
      const b64 = await new Promise<string>((resolve) => {
        reader.onload = () => resolve(reader.result as string);
        reader.readAsDataURL(file);
      });
      setSketchPreview(b64);

      const res = await fetch(`${API}/drawings/analyze-sketch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: b64 }),
      });
      if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
      const data = await res.json();

      // Populate from AI
      if (data.item_type) setItemType(data.item_type);
      if (data.name) setName(data.name);
      if (data.quote_num) setQuoteNum(data.quote_num);
      if (data.notes) setNotes(data.notes);
      if (data.dimensions && Object.keys(data.dimensions).length > 0) {
        setDimensions(data.dimensions);
      }

      // Bench-specific
      if (data.item_type === 'bench' && data.bench_details) {
        const bd = data.bench_details;
        if (bd.bench_type) setBenchType(bd.bench_type);
        if (bd.total_length_ft) setLf(bd.total_length_ft);
        else if (bd.leg1_length_ft && bd.leg2_length_ft) setLf(bd.leg1_length_ft + bd.leg2_length_ft);
        else if (bd.back_length_ft) setLf(bd.back_length_ft + (bd.left_depth_ft || 0) + (bd.right_depth_ft || 0));
      }

      const typeLabel = ITEM_TYPES.find(t => t.id === data.item_type)?.label || data.item_type;
      showStatus(`Detected: ${typeLabel} — ${Object.keys(data.dimensions || {}).length} dimensions extracted. Generating drawing...`, 6000);

      // Auto-generate drawing after analysis
      const genBody: Record<string, unknown> = {
        name: data.name || 'Drawing',
        item_type: data.item_type || 'generic',
        dimensions: data.dimensions || {},
        notes: data.notes || '',
        bench_type: data.bench_details?.bench_type || 'straight',
        lf: data.bench_details?.total_length_ft || 0,
        quote_num: data.quote_num || '',
      };
      try {
        const genRes = await fetch(`${API}/drawings/general`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(genBody),
        });
        const genData = await genRes.json();
        if (genData.svg) setSvgPreview(genData.svg);
      } catch { /* user can still click Generate manually */ }
    } catch {
      showStatus('Failed to analyze sketch');
    } finally {
      setSketchLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, []);

  const hasDimensions = Object.keys(dimensions).length > 0 || (itemType === 'bench' && lf > 0);

  const generatePreview = useCallback(async () => {
    if (!hasDimensions) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/drawings/general`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name || 'Drawing', item_type: itemType, dimensions, notes, bench_type: benchType, lf, quote_num: quoteNum }),
      });
      const data = await res.json();
      setSvgPreview(data.svg || '');
    } catch {
      showStatus('Preview generation failed');
    } finally {
      setLoading(false);
    }
  }, [hasDimensions, name, itemType, dimensions, notes, benchType, lf, quoteNum]);

  const downloadPdf = useCallback(async () => {
    if (!hasDimensions) return;
    setPdfLoading(true);
    try {
      const res = await fetch(`${API}/drawings/general/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name || 'Drawing', item_type: itemType, dimensions, notes, bench_type: benchType, lf, quote_num: quoteNum }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `drawing_${itemType}_${(name || 'item').replace(/\s+/g, '_')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      showStatus('PDF download failed');
    } finally {
      setPdfLoading(false);
    }
  }, [hasDimensions, name, itemType, dimensions, notes, benchType, lf, quoteNum]);

  const emailPdf = useCallback(async () => {
    setEmailLoading(true);
    try {
      const dimStr = Object.entries(dimensions).map(([k, v]) => `${k}: ${v}`).join(', ');
      const res = await fetch(`${API}/max/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Generate a ${itemType} drawing for "${name || 'Item'}" with dimensions: ${dimStr}. Email the PDF to empirebox2026@gmail.com`,
          channel: 'web_cc',
        }),
      });
      showStatus(res.ok ? 'Email sent!' : 'Failed to send');
    } catch {
      showStatus('Error sending email');
    } finally {
      setEmailLoading(false);
    }
  }, [itemType, name, dimensions]);

  const sendToDesk = useCallback(async (desk: string) => {
    const dimStr = Object.entries(dimensions).map(([k, v]) => `${k}: ${v}`).join(', ');
    try {
      const res = await fetch(`${API}/max/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Create a task for ${desk} desk: ${itemType} "${name || 'Item'}" — dimensions: ${dimStr}. ${notes}. Generate the architectural drawing PDF and attach it to the task.`,
          channel: 'web_cc',
        }),
      });
      showStatus(res.ok ? `Sent to ${desk}!` : 'Failed');
    } catch {
      showStatus('Error sending to desk');
    }
  }, [itemType, name, dimensions, notes]);

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '12px 14px', borderRadius: 10,
    border: '1.5px solid #e5e0d8', fontSize: 15, background: '#fff', color: '#333', outline: 'none', minHeight: 44,
  };
  const labelStyle: React.CSSProperties = {
    fontSize: 12, fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4, display: 'block',
  };
  const btnBase: React.CSSProperties = {
    padding: '14px 24px', borderRadius: 12, border: 'none', fontSize: 15, fontWeight: 700,
    cursor: 'pointer', minHeight: 48, minWidth: 48, transition: 'all 0.15s',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
  };

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{
          display: 'inline-block', background: 'linear-gradient(135deg, #b8960c, #d4af37)',
          color: '#1a1a2e', padding: '4px 14px', borderRadius: 16, fontSize: 11,
          fontWeight: 700, letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 10,
        }}>Drawing Studio</div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1a1a2e', margin: 0, lineHeight: 1.2 }}>
          Professional Drawings
        </h1>
        <p style={{ color: '#888', fontSize: 14, margin: '6px 0 0' }}>
          Upload any sketch or photo — AI identifies the item and generates a pro drawing with dimensions
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 24, alignItems: 'start' }}>
        {/* ── Left: Controls ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Upload */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 20, border: '1.5px dashed #b8960c' }}>
            <label style={labelStyle}>Upload Sketch or Photo</label>
            <p style={{ fontSize: 12, color: '#999', margin: '4px 0 12px' }}>
              Hand drawing, measurement sketch, or photo of the item — AI extracts everything
            </p>
            <input ref={fileInputRef} type="file" accept="image/*" capture="environment"
              onChange={handleSketchUpload} style={{ display: 'none' }} />
            <button onClick={() => fileInputRef.current?.click()} disabled={sketchLoading} style={{
              ...btnBase, width: '100%', padding: '12px 16px', fontSize: 14,
              background: sketchLoading ? '#eee' : 'linear-gradient(135deg, #b8960c, #d4af37)',
              color: sketchLoading ? '#999' : '#1a1a2e',
            }}>
              {sketchLoading ? 'Analyzing...' : sketchPreview ? 'Upload New' : 'Upload Sketch / Photo'}
            </button>
            {sketchPreview && (
              <img src={sketchPreview} alt="Sketch" style={{
                marginTop: 10, width: '100%', maxHeight: 160, objectFit: 'contain',
                borderRadius: 8, border: '1px solid #ece8e0',
              }} />
            )}
          </div>

          {/* Item Type */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
            <label style={labelStyle}>Item Type</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginTop: 6 }}>
              {ITEM_TYPES.map(t => (
                <button key={t.id} onClick={() => setItemType(t.id)} style={{
                  ...btnBase, padding: '8px 6px', fontSize: 11, flexDirection: 'column', gap: 1,
                  background: itemType === t.id ? '#fdf8eb' : '#f8f6f2',
                  border: itemType === t.id ? '2px solid #b8960c' : '2px solid transparent',
                  color: itemType === t.id ? '#96750a' : '#888',
                }}>
                  <span style={{ fontSize: 18 }}>{t.icon}</span>
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Name + Quote */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ flex: 2 }}>
                <label style={labelStyle}>Name</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Office Windows" style={inputStyle} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Quote #</label>
                <input value={quoteNum} onChange={e => setQuoteNum(e.target.value)} placeholder="EST-..." style={inputStyle} />
              </div>
            </div>
          </div>

          {/* Bench-specific: LF */}
          {itemType === 'bench' && (
            <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
              <label style={labelStyle}>Bench Details</label>
              <div style={{ display: 'flex', gap: 8, marginTop: 6, marginBottom: 10 }}>
                {['straight', 'l_shape', 'u_shape'].map(bt => (
                  <button key={bt} onClick={() => setBenchType(bt)} style={{
                    ...btnBase, flex: 1, padding: '8px', fontSize: 12,
                    background: benchType === bt ? '#fdf8eb' : '#f8f6f2',
                    border: benchType === bt ? '2px solid #b8960c' : '2px solid #e5e0d8',
                    color: benchType === bt ? '#96750a' : '#666',
                  }}>
                    {bt.replace('_', '-').replace(/\b\w/g, c => c.toUpperCase())}
                  </button>
                ))}
              </div>
              <label style={labelStyle}>Total Linear Feet</label>
              <input type="number" value={lf || ''} onChange={e => setLf(Number(e.target.value))} placeholder="0" style={inputStyle} />
            </div>
          )}

          {/* Dimensions */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
            <label style={labelStyle}>Dimensions</label>
            {Object.keys(dimensions).length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6, marginBottom: 10 }}>
                {Object.entries(dimensions).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#f8f6f2', padding: '8px 10px', borderRadius: 8 }}>
                    <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: '#555' }}>{k}</span>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#b8960c' }}>{v}</span>
                    <button onClick={() => removeDimension(k)} style={{
                      background: 'none', border: 'none', color: '#ccc', cursor: 'pointer', fontSize: 16, padding: '0 4px',
                    }}>×</button>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
              <input value={newDimLabel} onChange={e => setNewDimLabel(e.target.value)} placeholder="Label (e.g. Width)"
                style={{ ...inputStyle, flex: 1, fontSize: 13 }} onKeyDown={e => e.key === 'Enter' && addDimension()} />
              <input value={newDimValue} onChange={e => setNewDimValue(e.target.value)} placeholder='Value (e.g. 72")'
                style={{ ...inputStyle, flex: 1, fontSize: 13 }} onKeyDown={e => e.key === 'Enter' && addDimension()} />
              <button onClick={addDimension} style={{
                ...btnBase, padding: '8px 14px', fontSize: 18, background: '#f8f6f2', border: '1.5px solid #e5e0d8', color: '#b8960c',
              }}>+</button>
            </div>
          </div>

          {/* Notes */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
            <label style={labelStyle}>Notes</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder="Additional notes..."
              style={{ ...inputStyle, minHeight: 60, resize: 'vertical', fontFamily: 'inherit' }} />
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button onClick={generatePreview} disabled={loading || !hasDimensions} style={{
              ...btnBase, width: '100%',
              background: hasDimensions ? 'linear-gradient(135deg, #b8960c, #d4af37)' : '#ddd',
              color: hasDimensions ? '#1a1a2e' : '#999',
            }}>
              {loading ? 'Generating...' : 'Generate Drawing'}
            </button>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={downloadPdf} disabled={pdfLoading || !svgPreview} style={{
                ...btnBase, flex: 1, background: svgPreview ? '#1a1a2e' : '#eee', color: svgPreview ? '#d4af37' : '#bbb',
              }}>
                {pdfLoading ? '...' : 'Download PDF'}
              </button>
              <button onClick={emailPdf} disabled={emailLoading || !svgPreview} style={{
                ...btnBase, flex: 1, background: svgPreview ? '#16a34a' : '#eee', color: svgPreview ? '#fff' : '#bbb',
              }}>
                {emailLoading ? '...' : 'Email PDF'}
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => sendToDesk('Workroom')} disabled={!svgPreview} style={{
                ...btnBase, flex: 1, padding: '10px', fontSize: 12,
                background: svgPreview ? '#1a1a2e' : '#eee', color: svgPreview ? '#fff' : '#bbb',
              }}>Workroom</button>
              <button onClick={() => sendToDesk('WoodCraft')} disabled={!svgPreview} style={{
                ...btnBase, flex: 1, padding: '10px', fontSize: 12,
                background: svgPreview ? '#ca8a04' : '#eee', color: svgPreview ? '#fff' : '#bbb',
              }}>WoodCraft</button>
            </div>
            {statusMsg && (
              <div style={{
                textAlign: 'center', fontSize: 13, fontWeight: 600, padding: '8px', borderRadius: 8,
                background: statusMsg.includes('Detected') ? '#fdf8eb' : statusMsg.includes('sent') || statusMsg.includes('Sent') ? '#f0fdf4' : '#fef2f2',
                color: statusMsg.includes('Detected') ? '#b8960c' : statusMsg.includes('sent') || statusMsg.includes('Sent') ? '#16a34a' : '#ef4444',
              }}>
                {statusMsg}
              </div>
            )}
          </div>
        </div>

        {/* ── Right: Preview ── */}
        <div style={{
          background: '#fff', borderRadius: 14, border: '1px solid #ece8e0',
          minHeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
        }}>
          {svgPreview ? (
            <div dangerouslySetInnerHTML={{ __html: svgPreview }} style={{ width: '100%', padding: 16 }} />
          ) : (
            <div style={{ textAlign: 'center', color: '#ccc', padding: 40 }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>&#9998;</div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>Upload a sketch or enter dimensions</div>
              <div style={{ fontSize: 13, marginTop: 6 }}>AI generates professional drawings for any item type</div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @media (max-width: 768px) {
          div[style*="grid-template-columns: 380px"] { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
