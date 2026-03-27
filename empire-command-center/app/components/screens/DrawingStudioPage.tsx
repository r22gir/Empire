'use client';
import { useState, useCallback } from 'react';

const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : 'http://localhost:8000/api/v1';

type BenchType = 'straight' | 'l_shape' | 'u_shape';
type PanelStyle = 'flat' | 'vertical_channels' | 'horizontal_channels' | 'tufted';

const BENCH_TYPES: { id: BenchType; label: string; icon: string }[] = [
  { id: 'straight', label: 'Straight', icon: '▬' },
  { id: 'l_shape', label: 'L-Shape', icon: '⌐' },
  { id: 'u_shape', label: 'U-Shape', icon: '⊔' },
];

const PANEL_STYLES: { id: PanelStyle; label: string }[] = [
  { id: 'flat', label: 'Flat' },
  { id: 'vertical_channels', label: 'Vertical Channels' },
  { id: 'horizontal_channels', label: 'Horizontal Channels' },
  { id: 'tufted', label: 'Tufted' },
];

export default function DrawingStudioPage() {
  const [benchType, setBenchType] = useState<BenchType>('straight');
  const [panelStyle, setPanelStyle] = useState<PanelStyle>('flat');
  const [name, setName] = useState('');
  const [quoteNum, setQuoteNum] = useState('');
  const [svgPreview, setSvgPreview] = useState('');
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailStatus, setEmailStatus] = useState('');

  // Straight
  const [totalLength, setTotalLength] = useState(0);
  const [seatDepth, setSeatDepth] = useState(20);
  const [seatHeight, setSeatHeight] = useState(18);
  const [backHeight, setBackHeight] = useState(18);

  // L-shape
  const [leg1Length, setLeg1Length] = useState(0);
  const [leg2Length, setLeg2Length] = useState(0);

  // U-shape
  const [backLength, setBackLength] = useState(0);
  const [leftDepth, setLeftDepth] = useState(0);
  const [rightDepth, setRightDepth] = useState(0);

  const getLf = useCallback(() => {
    if (benchType === 'straight') return totalLength;
    if (benchType === 'l_shape') return leg1Length + leg2Length;
    return backLength + leftDepth + rightDepth;
  }, [benchType, totalLength, leg1Length, leg2Length, backLength, leftDepth, rightDepth]);

  const buildPayload = useCallback(() => ({
    bench_type: benchType,
    name: name || 'Bench',
    lf: getLf(),
    rate: 0,
    seat_depth: seatDepth,
    seat_height: seatHeight,
    back_height: backHeight,
    panel_style: panelStyle,
    quote_num: quoteNum,
    leg1_length: leg1Length,
    leg2_length: leg2Length,
    back_length: backLength,
    left_depth: leftDepth,
    right_depth: rightDepth,
  }), [benchType, name, getLf, seatDepth, seatHeight, backHeight, panelStyle, quoteNum, leg1Length, leg2Length, backLength, leftDepth, rightDepth]);

  const generatePreview = useCallback(async () => {
    if (getLf() <= 0) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/drawings/bench`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload()),
      });
      const data = await res.json();
      setSvgPreview(data.svg || '');
    } catch (e) {
      console.error('Preview failed:', e);
    } finally {
      setLoading(false);
    }
  }, [getLf, buildPayload]);

  const downloadPdf = useCallback(async () => {
    if (getLf() <= 0) return;
    setPdfLoading(true);
    try {
      const res = await fetch(`${API}/drawings/bench/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload()),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bench_drawing_${benchType}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('PDF download failed:', e);
    } finally {
      setPdfLoading(false);
    }
  }, [getLf, buildPayload, benchType]);

  const emailPdf = useCallback(async () => {
    if (getLf() <= 0) return;
    setEmailLoading(true);
    setEmailStatus('');
    try {
      // Generate PDF first, then send via MAX chat
      const res = await fetch(`${API}/max/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Generate a ${benchType.replace('_', '-')} bench drawing for "${name || 'Bench'}" (${getLf()} LF) and email it to empirebox2026@gmail.com`,
          channel: 'web_cc',
        }),
      });
      if (res.ok) {
        setEmailStatus('Email sent!');
      } else {
        setEmailStatus('Failed to send');
      }
    } catch (e) {
      setEmailStatus('Error sending email');
    } finally {
      setEmailLoading(false);
      setTimeout(() => setEmailStatus(''), 4000);
    }
  }, [getLf, benchType, name]);

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '12px 14px',
    borderRadius: 10,
    border: '1.5px solid #e5e0d8',
    fontSize: 15,
    background: '#fff',
    color: '#333',
    outline: 'none',
    minHeight: 44,
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 12,
    fontWeight: 600,
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
    display: 'block',
  };

  const btnBase: React.CSSProperties = {
    padding: '14px 24px',
    borderRadius: 12,
    border: 'none',
    fontSize: 15,
    fontWeight: 700,
    cursor: 'pointer',
    minHeight: 48,
    minWidth: 48,
    transition: 'all 0.15s',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  };

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{
          display: 'inline-block',
          background: 'linear-gradient(135deg, #b8960c, #d4af37)',
          color: '#1a1a2e',
          padding: '4px 14px',
          borderRadius: 16,
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: 1.2,
          textTransform: 'uppercase',
          marginBottom: 10,
        }}>Drawing Studio</div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1a1a2e', margin: 0, lineHeight: 1.2 }}>
          Architectural Bench Drawings
        </h1>
        <p style={{ color: '#888', fontSize: 14, margin: '6px 0 0' }}>
          Generate professional isometric 3D drawings with dimension callouts
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 24, alignItems: 'start' }}>
        {/* ── Left: Controls ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Bench Type */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 20, border: '1px solid #ece8e0' }}>
            <label style={labelStyle}>Bench Type</label>
            <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
              {BENCH_TYPES.map(bt => (
                <button key={bt.id} onClick={() => setBenchType(bt.id)} style={{
                  ...btnBase,
                  flex: 1,
                  padding: '12px 8px',
                  fontSize: 13,
                  background: benchType === bt.id ? '#fdf8eb' : '#f8f6f2',
                  border: benchType === bt.id ? '2px solid #b8960c' : '2px solid #e5e0d8',
                  color: benchType === bt.id ? '#96750a' : '#666',
                  flexDirection: 'column',
                  gap: 2,
                }}>
                  <span style={{ fontSize: 22 }}>{bt.icon}</span>
                  {bt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Dimensions */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 20, border: '1px solid #ece8e0' }}>
            <label style={labelStyle}>Dimensions</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 8 }}>
              <div>
                <label style={labelStyle}>Name</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Main Dining Bench" style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Quote #</label>
                <input value={quoteNum} onChange={e => setQuoteNum(e.target.value)} placeholder="e.g. EST-2026-075" style={inputStyle} />
              </div>

              {benchType === 'straight' && (
                <div>
                  <label style={labelStyle}>Total Length (feet)</label>
                  <input type="number" value={totalLength || ''} onChange={e => setTotalLength(Number(e.target.value))} placeholder="0" style={inputStyle} />
                </div>
              )}

              {benchType === 'l_shape' && (<>
                <div>
                  <label style={labelStyle}>Leg 1 Length (feet)</label>
                  <input type="number" value={leg1Length || ''} onChange={e => setLeg1Length(Number(e.target.value))} placeholder="0" style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Leg 2 Length (feet)</label>
                  <input type="number" value={leg2Length || ''} onChange={e => setLeg2Length(Number(e.target.value))} placeholder="0" style={inputStyle} />
                </div>
              </>)}

              {benchType === 'u_shape' && (<>
                <div>
                  <label style={labelStyle}>Back Length (feet)</label>
                  <input type="number" value={backLength || ''} onChange={e => setBackLength(Number(e.target.value))} placeholder="0" style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Left Depth (feet)</label>
                  <input type="number" value={leftDepth || ''} onChange={e => setLeftDepth(Number(e.target.value))} placeholder="0" style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Right Depth (feet)</label>
                  <input type="number" value={rightDepth || ''} onChange={e => setRightDepth(Number(e.target.value))} placeholder="0" style={inputStyle} />
                </div>
              </>)}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                <div>
                  <label style={labelStyle}>Seat Depth (")</label>
                  <input type="number" value={seatDepth || ''} onChange={e => setSeatDepth(Number(e.target.value))} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Seat Height (")</label>
                  <input type="number" value={seatHeight || ''} onChange={e => setSeatHeight(Number(e.target.value))} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Back Height (")</label>
                  <input type="number" value={backHeight || ''} onChange={e => setBackHeight(Number(e.target.value))} style={inputStyle} />
                </div>
              </div>
            </div>
          </div>

          {/* Panel Style */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 20, border: '1px solid #ece8e0' }}>
            <label style={labelStyle}>Panel Style</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 6 }}>
              {PANEL_STYLES.map(ps => (
                <button key={ps.id} onClick={() => setPanelStyle(ps.id)} style={{
                  ...btnBase,
                  padding: '10px 12px',
                  fontSize: 13,
                  background: panelStyle === ps.id ? '#fdf8eb' : '#f8f6f2',
                  border: panelStyle === ps.id ? '2px solid #b8960c' : '2px solid #e5e0d8',
                  color: panelStyle === ps.id ? '#96750a' : '#666',
                }}>
                  {ps.label}
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button onClick={generatePreview} disabled={loading || getLf() <= 0} style={{
              ...btnBase,
              background: getLf() > 0 ? 'linear-gradient(135deg, #b8960c, #d4af37)' : '#ddd',
              color: getLf() > 0 ? '#1a1a2e' : '#999',
              width: '100%',
            }}>
              {loading ? 'Generating...' : 'Generate Preview'}
            </button>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={downloadPdf} disabled={pdfLoading || !svgPreview} style={{
                ...btnBase,
                flex: 1,
                background: svgPreview ? '#1a1a2e' : '#eee',
                color: svgPreview ? '#d4af37' : '#bbb',
              }}>
                {pdfLoading ? 'Generating...' : 'Download PDF'}
              </button>
              <button onClick={emailPdf} disabled={emailLoading || !svgPreview} style={{
                ...btnBase,
                flex: 1,
                background: svgPreview ? '#16a34a' : '#eee',
                color: svgPreview ? '#fff' : '#bbb',
              }}>
                {emailLoading ? 'Sending...' : 'Email PDF'}
              </button>
            </div>
            {emailStatus && (
              <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 600, color: emailStatus.includes('sent') ? '#16a34a' : '#ef4444' }}>
                {emailStatus}
              </div>
            )}
          </div>
        </div>

        {/* ── Right: SVG Preview ── */}
        <div style={{
          background: '#fff',
          borderRadius: 14,
          border: '1px solid #ece8e0',
          minHeight: 500,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}>
          {svgPreview ? (
            <div
              dangerouslySetInnerHTML={{ __html: svgPreview }}
              style={{ width: '100%', padding: 16 }}
            />
          ) : (
            <div style={{ textAlign: 'center', color: '#ccc', padding: 40 }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>&#9998;</div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>Enter dimensions and click Generate Preview</div>
              <div style={{ fontSize: 13, marginTop: 6 }}>Isometric 3D drawing with dimension callouts</div>
            </div>
          )}
        </div>
      </div>

      {/* Mobile responsive override */}
      <style>{`
        @media (max-width: 768px) {
          div[style*="grid-template-columns: 380px"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
